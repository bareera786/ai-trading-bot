from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_required, current_user, login_user
import pyotp
import qrcode
import io
import base64
from app.models import db, User
from app.extensions import limiter

two_factor_bp = Blueprint('two_factor', __name__, url_prefix='/auth/2fa')

@two_factor_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """Setup 2FA for the first time."""
    if current_user.is_2fa_enabled:
        flash("2FA is already enabled.", "info")
        return redirect(url_for('dashboard_bp.dashboard'))

    # Generate secret if not exists
    if not current_user.totp_secret:
        current_user.totp_secret = pyotp.random_base32()
        db.session.commit()

    if request.method == 'POST':
        # Verify code to activate
        code = request.form.get('code')
        totp = pyotp.TOTP(current_user.totp_secret)
        if totp.verify(code):
            current_user.is_2fa_enabled = True
            db.session.commit()
            flash("Two-Factor Authentication Enabled!", "success")
            return redirect(url_for('dashboard_bp.dashboard'))
        else:
            flash("Invalid code. Please try again.", "danger")

    # Generate QR Code
    totp_uri = pyotp.totp.TOTP(current_user.totp_secret).provisioning_uri(
        name=current_user.email,
        issuer_name="AI Trading Bot"
    )
    
    img = qrcode.make(totp_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return render_template('auth/2fa_setup.html', secret=current_user.totp_secret, qr_code=qr_code_base64)

@two_factor_bp.route('/disable', methods=['POST'])
@login_required
def disable():
    """Disable 2FA."""
    # In a real app, require password confirmation here
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.session.commit()
    flash("2FA Disabled.", "warning")
    return redirect(url_for('dashboard_bp.dashboard'))

@two_factor_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    """Verify 2FA during login."""
    if not session.get('partial_user_id'):
        return redirect(url_for('auth_bp.login'))

    if request.method == 'POST':
        user_id = session.get('partial_user_id')
        user = User.query.get(user_id)
        code = request.form.get('code')

        if user and user.totp_secret:
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code):
                # Complete login
                session.pop('partial_user_id', None)
                login_user(user)
                flash("Login successful.", "success")
                next_page = session.get('next_url')
                session.pop('next_url', None) # Clear it
                return redirect(next_page or url_for('dashboard_bp.dashboard'))
            else:
                flash("Invalid 2FA code.", "danger")
        else:
             flash("User not found or 2FA not set up.", "danger")
             return redirect(url_for('auth_bp.login'))

    return render_template('auth/2fa_verify.html')
