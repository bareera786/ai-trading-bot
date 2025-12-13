"""Authentication views blueprint."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.models import User
from app.routes.utils import marketing_analytics_context
from app.utils.email_utils import (
    send_password_reset_email,
    send_email_verification_email,
)
from app.utils.password_utils import validate_password_strength


auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
@limiter.limit("20 per minute")
def login():
    """Handle login via form or JSON payload."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    error_message = "Invalid username or password"
    active_tab = "login"

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
        else:
            username = request.form.get("username")
            password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # Check if account is locked
        if user and user.locked_until and user.locked_until > datetime.utcnow():
            remaining_time = user.locked_until - datetime.utcnow()
            minutes_left = int(remaining_time.total_seconds() / 60)
            error_message = f"Account is locked due to too many failed login attempts. Try again in {minutes_left} minutes."
            logger.warning(
                f"Login attempt for locked account: {username} from IP {request.remote_addr}"
            )
            if request.is_json:
                return jsonify({"error": error_message}), 429
            flash(error_message)
            return render_template(
                "auth/auth.html",
                analytics=marketing_analytics_context(),
                active_tab=active_tab,
            )

        if user and user.check_password(password):
            if not user.email_verified and not user.is_admin:
                flash("Please verify your email address before logging in.")
                return redirect(url_for("auth.login"))

            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()

            login_user(user)
            logger.info(
                f"User {username} logged in successfully from IP {request.remote_addr}"
            )
            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "message": "Login successful",
                        "user": {
                            "username": user.username,
                            "is_admin": user.is_admin,
                            "id": user.id,
                        },
                    }
                )
            next_page = request.args.get("next")
            response = (
                redirect(next_page)
                if next_page
                else redirect(url_for("dashboard_bp.dashboard"))
            )
            response.headers[
                "Cache-Control"
            ] = "no-cache, no-store, must-revalidate, max-age=0, private, no-transform"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        else:
            # Handle failed login attempt
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

                # Lock account after 5 failed attempts for 15 minutes
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                    error_message = "Account locked due to too many failed login attempts. Try again in 15 minutes."
                    logger.warning(
                        f"Account locked for user {username} after {user.failed_login_attempts} failed attempts from IP {request.remote_addr}"
                    )
                else:
                    remaining_attempts = 5 - user.failed_login_attempts
                    error_message = f"Invalid username or password. {remaining_attempts} attempts remaining before account lockout."

                db.session.commit()
            else:
                logger.warning(
                    f"Failed login attempt for non-existent username '{username}' from IP {request.remote_addr}"
                )

        if request.is_json:
            return jsonify({"error": error_message}), 401

        flash(error_message)

    return render_template(
        "auth/auth.html", analytics=marketing_analytics_context(), active_tab=active_tab
    )


@auth_bp.route("/logout", endpoint="logout")
@login_required
def logout():
    """Destroy the active session and redirect to login."""
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"], endpoint="register")
@limiter.limit("10 per minute")
def register():
    """Render or process the registration form."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    active_tab = "register"

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        captcha = request.form.get("captcha")

        if captcha != "7":
            flash("CAPTCHA verification failed")
            return redirect(url_for("auth.register"))

        if not email or "@" not in email or "." not in email:
            flash("Please enter a valid email address")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("auth.register"))

        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg)
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email, is_admin=False, is_active=True)
        user.set_password(password)

        # Generate email verification token
        token = user.generate_email_verification_token()
        user.email_verification_token = token
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)

        db.session.add(user)
        db.session.commit()

        # Send email verification
        send_email_verification_email(user.email, token)

        logger.info(
            f"New user registered: {username} ({email}) from IP {request.remote_addr}"
        )

        flash(
            "Registration successful! Please check your email to verify your account before logging in."
        )
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/auth.html", analytics=marketing_analytics_context(), active_tab=active_tab
    )


@auth_bp.route("/forgot-password", methods=["GET", "POST"], endpoint="forgot_password")
def forgot_password():
    """Handle forgot password requests."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_password_reset_token()
            send_password_reset_email(user.email, token)
            flash(
                "If an account with that email exists, a password reset link has been sent."
            )
            logger.info(f"Password reset email sent to: {email}")
        else:
            flash(
                "If an account with that email exists, a password reset link has been sent."
            )
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/forgot_password.html", analytics=marketing_analytics_context()
    )


@auth_bp.route(
    "/reset-password/<token>", methods=["GET", "POST"], endpoint="reset_password"
)
def reset_password(token):
    """Handle password reset with token."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    user = User.verify_password_reset_token(token)
    if not user:
        flash("Invalid or expired reset token.")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(request.url)

        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg)
            return redirect(request.url)

        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        flash("Password has been reset successfully. Please login.")
        logger.info(f"Password reset successful for user: {user.username}")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset_password.html", analytics=marketing_analytics_context(), token=token
    )


@auth_bp.route("/verify-email/<token>", endpoint="verify_email")
def verify_email(token):
    """Handle email verification with token."""
    user = User.query.filter_by(email_verification_token=token).first()
    if not user or not user.verify_email_verification_token(token):
        flash("Invalid or expired verification token.")
        return redirect(url_for("auth.login"))

    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.session.commit()

    flash("Email verified successfully! You can now log in.")
    logger.info(f"Email verified for user: {user.username}")
    return redirect(url_for("auth.login"))
