from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, UserPortfolio, ExchangeCredential, User
from app.extensions import limiter
from app.security.credential_manager import CredentialManager

cred_manager = CredentialManager()

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')

@onboarding_bp.route('/', methods=['GET'])
@login_required
def wizard():
    """Render the onboarding wizard."""
    # Check if user already has portfolio/credentials to possibly skip or pre-fill
    portfolio = UserPortfolio.query.filter_by(user_id=current_user.id).first()
    has_keys = ExchangeCredential.query.filter_by(user_id=current_user.id).first() is not None
    
    return render_template(
        'onboarding/wizard.html', 
        portfolio=portfolio,
        has_keys=has_keys
    )

@onboarding_bp.route('/api/step/exchange', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def save_exchange():
    """Step 1: Save Exchange Credentials or enable Paper Trading."""
    data = request.json
    mode = data.get('mode') # 'paper' or 'real'
    
    try:
        if mode == 'real':
            # In a real app, encryption would happen here or in a service
            # For this MVP, we mock the credential creation/update
            api_key = data.get('api_key')
            api_secret = data.get('api_secret')
            exchange_id = data.get('exchange_id', 'binance')
            
            if not api_key or not api_secret:
                return jsonify({'success': False, 'error': 'Missing API Credentials'}), 400
                
            # Create or update existing
            cred = ExchangeCredential.query.filter_by(user_id=current_user.id, exchange_id=exchange_id).first()
            
            # Encrypt credentials
            enc_key, enc_secret = cred_manager.encrypt_credentials(api_key, api_secret)
            
            if not cred:
                cred = ExchangeCredential(
                    user_id=current_user.id,
                    exchange_id=exchange_id,
                    api_key_enc=enc_key,
                    api_secret_enc=enc_secret
                )
                db.session.add(cred)
            else:
                cred.api_key_enc = enc_key
                cred.api_secret_enc = enc_secret
            
            # Update user features
            # current_user.features['live_trading'] = True (if stored in JSON)
            
        # Ensure portfolio exists
        portfolio = UserPortfolio.query.filter_by(user_id=current_user.id).first()
        if not portfolio:
            portfolio = UserPortfolio(user_id=current_user.id)
            db.session.add(portfolio)
            
        portfolio.auto_trade_enabled = False # Safety first
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/api/step/risk', methods=['POST'])
@login_required
def save_risk():
    """Step 2: Save Risk Preference."""
    data = request.json
    risk_level = data.get('risk_level', 'moderate') # conservative, moderate, aggressive
    
    try:
        portfolio = UserPortfolio.query.filter_by(user_id=current_user.id).first()
        if not portfolio:
            portfolio = UserPortfolio(user_id=current_user.id)
            db.session.add(portfolio)
        
        portfolio.risk_preference = risk_level
        # Set some defaults based on risk
        if risk_level == 'conservative':
            portfolio.max_position_size = 500
            portfolio.stop_loss = 0.02 # 2%
        elif risk_level == 'aggressive':
            portfolio.max_position_size = 2000
            portfolio.stop_loss = 0.05 # 5%
        else:
            portfolio.max_position_size = 1000
            portfolio.stop_loss = 0.03 # 3%
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/api/step/complete', methods=['POST'])
@login_required
def complete_onboarding():
    """Final Step: Mark as complete from session perspective."""
    session['onboarding_completed'] = True
    return jsonify({'success': True, 'redirect': url_for('dashboard_bp.dashboard')})
