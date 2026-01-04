from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.models import SubscriptionPlan, User
from app.services.binance import BinanceCredentialService, BinanceCredentialStore
from app.subscriptions.helpers import assign_subscription_to_user, normalize_plan_code, serialize_subscription

admin_user_api_bp = Blueprint("admin_user_api", __name__, url_prefix="/api/users")


def _coerce_int(value, *, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except Exception:
        return None


def _subscription_end_iso(subscription) -> str | None:
    if not subscription:
        return None
    end = getattr(subscription, "current_period_end", None) or getattr(subscription, "trial_end", None)
    return end.isoformat() if end else None


@admin_user_api_bp.route("", methods=["GET"])
@login_required
@limiter.exempt
def list_users():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    search = request.args.get("search", "")
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (User.id == search if search.isdigit() else False)
        )
    users = query.order_by(User.id.desc()).all()
    return jsonify(
        {
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "balance": getattr(u, "balance", 0.0),  # Default to 0 if not set
                    "portfolio_value": getattr(
                        u, "portfolio_value", 0.0
                    ),  # Add if available
                    "trade_count": len(u.trades) if u.trades else 0,
                    "subscription_expiry": _subscription_end_iso(u.active_subscription),
                    "subscription_history": [
                        {
                            "plan": s.plan.code if s.plan else "unknown",
                            "start": s.created_at.isoformat() if s.created_at else None,
                            "end": _subscription_end_iso(s),
                            "is_active": bool(getattr(s, "is_active", False)),
                        }
                        for s in u.subscriptions
                    ]
                    if u.subscriptions
                    else [],
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                }
                for u in users
            ]
        }
    )


@admin_user_api_bp.route("/<int:user_id>", methods=["GET"])
@login_required
@limiter.exempt
def get_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "balance": getattr(user, "balance", 0.0),
            "portfolio_value": getattr(user, "portfolio_value", 0.0),
            "trade_count": len(user.trades) if user.trades else 0,
            "subscription_expiry": _subscription_end_iso(user.active_subscription),
            "subscription_history": [
                {
                    "plan": s.plan.code if s.plan else "unknown",
                    "start": s.created_at.isoformat() if s.created_at else None,
                    "end": _subscription_end_iso(s),
                    "is_active": bool(getattr(s, "is_active", False)),
                }
                for s in user.subscriptions
            ]
            if user.subscriptions
            else [],
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
    )


@admin_user_api_bp.route(
    "/<int:user_id>/credentials", methods=["GET"], endpoint="admin_get_user_credentials"
)
@login_required
@limiter.exempt
def admin_get_user_credentials(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    ctx = current_app.extensions.get("ai_bot_context") or {}
    credentials_store: Optional[BinanceCredentialStore] = ctx.get(
        "binance_credentials_store"
    )
    credential_service: Optional[BinanceCredentialService] = ctx.get(
        "binance_credential_service"
    )
    if not credentials_store:
        return jsonify({"error": "Credential store unavailable"}), 500

    creds = credentials_store.get_credentials(user_id=user_id)
    status = None
    if credential_service:
        status = credential_service.get_status(
            include_connection=False, include_logs=False, user_id=user_id
        )

    return jsonify({"credentials": creds, "status": status})


@admin_user_api_bp.route(
    "/<int:user_id>/credentials",
    methods=["POST"],
    endpoint="admin_set_user_credentials",
)
@login_required
@limiter.exempt
def admin_set_user_credentials(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    api_key = (data.get("apiKey") or data.get("api_key") or "").strip()
    api_secret = (data.get("apiSecret") or data.get("api_secret") or "").strip()
    testnet = data.get("testnet", True)
    account_type = data.get("accountType") or data.get("account_type") or "spot"

    ctx = current_app.extensions.get("ai_bot_context") or {}
    credentials_store: Optional[BinanceCredentialStore] = ctx.get(
        "binance_credentials_store"
    )
    if not credentials_store:
        return jsonify({"error": "Credential store unavailable"}), 500

    if not api_key or not api_secret:
        return jsonify({"error": "API key and secret are required"}), 400

    saved = credentials_store.save_credentials(
        api_key, api_secret, testnet=testnet, account_type=account_type, user_id=user_id
    )
    return jsonify({"saved": True, "credentials": saved})


@admin_user_api_bp.route(
    "/<int:user_id>/credentials",
    methods=["DELETE"],
    endpoint="admin_clear_user_credentials",
)
@login_required
@limiter.exempt
def admin_clear_user_credentials(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    account_type = data.get("accountType") or data.get("account_type")

    ctx = current_app.extensions.get("ai_bot_context") or {}
    credentials_store: Optional[BinanceCredentialStore] = ctx.get(
        "binance_credentials_store"
    )
    if not credentials_store:
        return jsonify({"error": "Credential store unavailable"}), 500

    if account_type:
        credentials_store.clear_credentials(account_type, user_id=user_id)
    else:
        credentials_store.clear_credentials(user_id=user_id)

    return jsonify({"cleared": True})


@admin_user_api_bp.route(
    "/<int:user_id>/credentials/test",
    methods=["POST"],
    endpoint="admin_test_user_credentials",
)
@login_required
@limiter.exempt
def admin_test_user_credentials(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    api_key = (data.get("apiKey") or data.get("api_key") or "").strip()
    api_secret = (data.get("apiSecret") or data.get("api_secret") or "").strip()
    testnet = data.get("testnet", True)

    ctx = current_app.extensions.get("ai_bot_context") or {}
    credential_service: Optional[BinanceCredentialService] = ctx.get(
        "binance_credential_service"
    )
    if not credential_service:
        return jsonify({"error": "Credential service unavailable"}), 500

    if not api_key or not api_secret:
        return jsonify({"error": "API key and secret are required for testing"}), 400

    result = credential_service.test_credentials(api_key, api_secret, testnet=testnet)
    return jsonify(result)


@admin_user_api_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
@limiter.exempt
def toggle_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.is_active = data.get("is_active", not user.is_active)
    db.session.commit()
    return jsonify({"success": True, "is_active": user.is_active})


@admin_user_api_bp.route("/<int:user_id>", methods=["PUT"])
@login_required
@limiter.exempt
def edit_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    if "balance" in data:
        user.balance = float(data["balance"]) if data["balance"] else 0.0
    if "portfolio_value" in data:
        user.portfolio_value = (
            float(data["portfolio_value"]) if data["portfolio_value"] else 0.0
        )
    # Subscription expiry update (if applicable)
    if (
        "subscription_expiry" in data
        and hasattr(user, "active_subscription")
        and user.active_subscription
    ):
        requested_end = _safe_parse_iso_datetime(data.get("subscription_expiry"))
        if requested_end:
            user.active_subscription.current_period_end = requested_end
    db.session.commit()
    return jsonify({"success": True})


@admin_user_api_bp.route("/<int:user_id>/subscription/grant", methods=["POST"])
@login_required
@limiter.exempt
def admin_grant_subscription(user_id: int):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    plan_code = normalize_plan_code(data.get("plan_code") or "pro-monthly")
    notes = (data.get("notes") or "").strip() or None
    days_override = _coerce_int(data.get("days"), default=None)

    plan = SubscriptionPlan.query.filter_by(code=plan_code).first()
    if not plan:
        return jsonify({"error": "Subscription plan not found"}), 404
    if not plan.is_active:
        return jsonify({"error": "Cannot assign an inactive plan"}), 400

    subscription = assign_subscription_to_user(
        user,
        plan,
        trial_days=0,
        auto_renew=False,
        cancel_existing=True,
        notes=notes or "Admin-granted access",
    )

    if days_override is not None and days_override > 0:
        now = datetime.utcnow()
        subscription.status = "active"
        subscription.trial_end = None
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=days_override)
        subscription.next_billing_date = None
        subscription.auto_renew = False
        suffix = f"{datetime.utcnow().isoformat()}: Admin override duration_days={days_override}"
        subscription.notes = (
            f"{subscription.notes}\n{suffix}" if subscription.notes else suffix
        )
        db.session.commit()

    return jsonify({"success": True, "subscription": serialize_subscription(subscription)})


@admin_user_api_bp.route("/<int:user_id>/subscription/extend", methods=["POST"])
@login_required
@limiter.exempt
def admin_extend_subscription(user_id: int):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    user = User.query.get_or_404(user_id)
    subscription = user.active_subscription
    if not subscription or not getattr(subscription, "is_active", False):
        return jsonify({"error": "User does not have an active subscription"}), 400

    data = request.get_json(silent=True) or {}
    days = _coerce_int(data.get("days"), default=None)
    if days is None or days <= 0:
        return jsonify({"error": "days must be a positive integer"}), 400
    notes = (data.get("notes") or "").strip() or None

    base_end = getattr(subscription, "current_period_end", None) or datetime.utcnow()
    if base_end < datetime.utcnow():
        base_end = datetime.utcnow()
    subscription.current_period_end = base_end + timedelta(days=days)
    subscription.status = "active"
    subscription.cancel_at_period_end = False
    subscription.auto_renew = False

    if notes:
        note = f"{datetime.utcnow().isoformat()}: {notes}"
    else:
        note = f"{datetime.utcnow().isoformat()}: Admin extended subscription by {days} day(s)"
    subscription.notes = f"{subscription.notes}\n{note}" if subscription.notes else note

    db.session.commit()
    return jsonify({"success": True, "subscription": serialize_subscription(subscription)})
