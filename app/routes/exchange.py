"""Routes for managing exchange connections."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ExchangeCredential
from app.security.credential_manager import CredentialManager
from app.services.ccxt_adapter import CCXTAdapter

exchange_bp = Blueprint("exchange", __name__, url_prefix="/api/exchange")
cred_manager = CredentialManager()

@exchange_bp.route("/settings", methods=["GET"])
@login_required
def exchange_settings_ui():
    """Render new exchange connection page."""
    return render_template("exchange_connect.html")

@exchange_bp.route("/connect", methods=["POST"])
@login_required
def connect_exchange():
    """Connect a new exchange."""
    data = request.get_json()
    exchange_id = data.get("exchange_id")
    api_key = data.get("api_key")
    api_secret = data.get("api_secret")
    subaccount = data.get("subaccount")

    if not all([exchange_id, api_key, api_secret]):
        return jsonify({"error": "Missing credentials"}), 400

    # 1. Validate connection via CCXT
    exchange = CCXTAdapter.get_exchange(exchange_id, api_key, api_secret)
    if not exchange:
        return jsonify({"error": "Failed to initialize exchange client"}), 400
    
    # Try fetching balance to verify keys
    try:
        CCXTAdapter.fetch_balance(exchange)
    except Exception as e:
        return jsonify({"error": f"Connection failed: {str(e)}"}), 400

    # 2. Encrypt and Save
    enc_key, enc_secret = cred_manager.encrypt_credentials(api_key, api_secret)
    
    # Check if exists
    existing = ExchangeCredential.query.filter_by(
        user_id=current_user.id, 
        exchange_id=exchange_id,
        subaccount=subaccount
    ).first()

    if existing:
        existing.api_key_enc = enc_key
        existing.api_secret_enc = enc_secret
        existing.is_active = True
        msg = "Credentials updated"
    else:
        new_cred = ExchangeCredential(
            user_id=current_user.id,
            exchange_id=exchange_id,
            api_key_enc=enc_key,
            api_secret_enc=enc_secret,
            subaccount=subaccount
        )
        db.session.add(new_cred)
        msg = "Exchange connected successfully"

    db.session.commit()
    return jsonify({"message": msg, "exchange": exchange_id})

@exchange_bp.route("/list", methods=["GET"])
@login_required
def list_exchanges():
    """List connected exchanges."""
    creds = ExchangeCredential.query.filter_by(user_id=current_user.id, is_active=True).all()
    return jsonify({
        "exchanges": [
            {
                "exchange_id": c.exchange_id,
                "subaccount": c.subaccount,
                "connected_at": c.created_at.isoformat()
            } for c in creds
        ]
    })

@exchange_bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect_exchange():
    """Deactivate an exchange connection."""
    data = request.get_json()
    exchange_id = data.get("exchange_id")
    subaccount = data.get("subaccount")
    
    cred = ExchangeCredential.query.filter_by(
        user_id=current_user.id, 
        exchange_id=exchange_id,
        subaccount=subaccount
    ).first()
    
    if cred:
        cred.is_active = False
        db.session.commit()
        return jsonify({"message": "Exchange disconnected"})
    
    return jsonify({"error": "Credential not found"}), 404
