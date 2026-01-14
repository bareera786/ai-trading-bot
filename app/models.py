"""Database models for the Ultimate AI Trading Bot."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
import enum

from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, abort
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String
from sqlalchemy import Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from functools import wraps

from .extensions import db, login_manager

Base = declarative_base()


class RoleEnum(enum.Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


# DEPRECATED: Keeping for migration compatibility, but not used in new User model


class User(Base, UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    selected_symbols = db.Column(db.Text, default="[]")
    custom_symbols = db.Column(db.Text, default="[]")
    
    # Additional fields for compatibility
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_selected_symbols(self) -> list[str]:
        try:
            return json.loads(self.selected_symbols or "[]")
        except json.JSONDecodeError:
            return []

    def set_selected_symbols(self, symbols: list[str]) -> None:
        self.selected_symbols = json.dumps(symbols)

    def get_custom_symbols(self) -> list[str]:
        try:
            return json.loads(self.custom_symbols or "[]")
        except json.JSONDecodeError:
            return []

    def set_custom_symbols(self, symbols: list[str]) -> None:
        self.custom_symbols = json.dumps(symbols)

    @property
    def is_premium(self) -> bool:
        # For simplified model, admins are considered premium
        return self.is_admin

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.__dict__.get('is_active', True)

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.__dict__['is_active'] = value

    def is_account_locked(self):
        """Check if the account is currently locked."""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def increment_failed_logins(self):
        """Increment failed login attempts and lock account if threshold is reached."""
        self.failed_login_count += 1
        if self.failed_login_count >= current_app.config.get("MAX_FAILED_LOGINS", 5):
            self.locked_until = datetime.utcnow() + timedelta(minutes=current_app.config.get("LOCKOUT_DURATION", 15))

    def reset_failed_logins(self):
        """Reset failed login attempts."""
        self.failed_login_count = 0
        self.locked_until = None

    @property
    def failed_login_attempts(self):
        """Backward-compatible alias for legacy code."""
        return getattr(self, "failed_login_count", 0)

    @failed_login_attempts.setter
    def failed_login_attempts(self, value):
        self.failed_login_count = value


class UserTrade(Base, db.Model):
    __tablename__ = "user_trade"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=False)
    symbol = db.Column(db.String(20))
    trade_type = db.Column(db.String(20))
    side = db.Column(db.String(10))
    quantity = db.Column(db.Float)
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, default=0.0)
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="open")
    signal_source = db.Column(db.String(50))
    confidence_score = db.Column(db.Float)
    leverage = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    cost_basis = db.Column(db.Float, default=0.0)
    realized_gains = db.Column(db.Float, default=0.0)
    holding_period = db.Column(db.Integer, default=0)
    tax_lot_id = db.Column(db.String(50))


class UserPortfolio(Base, db.Model):
    __tablename__ = "user_portfolio"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=False)
    symbol = db.Column(db.String(20), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    avg_price = db.Column(db.Float, default=0.0)
    current_price = db.Column(db.Float, default=0.0)
    pnl = db.Column(db.Float, default=0.0)
    pnl_percent = db.Column(db.Float, default=0.0)
    max_position_size = db.Column(db.Float, default=1000.0)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)
    auto_trade_enabled = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(20), default="medium")

    total_balance = db.Column(db.Float, default=10000.0)
    available_balance = db.Column(db.Float, default=10000.0)
    total_profit_loss = db.Column(db.Float, default=0.0)
    daily_pnl = db.Column(db.Float, default=0.0)
    open_positions = db.Column(db.JSON, default=dict)
    risk_preference = db.Column(db.String(20), default="moderate")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class SubscriptionPlan(Base, db.Model):
    __tablename__ = "subscription_plan"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    plan_type = db.Column(db.String(20), nullable=False, default="monthly")
    price_usd = db.Column(db.Numeric(10, 2), default=0)
    currency = db.Column(db.String(8), default="USD")
    duration_days = db.Column(db.Integer, nullable=False)
    trial_days = db.Column(db.Integer, default=0)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    subscriptions = db.relationship("UserSubscription", backref="plan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "plan_type": self.plan_type,
            "price_usd": float(self.price_usd or 0),
            "currency": self.currency,
            "duration_days": self.duration_days,
            "trial_days": self.trial_days,
            "description": self.description,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSubscription(Base, db.Model):
    __tablename__ = "user_subscription"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=False)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("subscription_plan.id"), nullable=False
    )
    status = db.Column(db.String(20), default="trialing")
    trial_end = db.Column(db.DateTime, nullable=True)
    current_period_start = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime, nullable=True)
    next_billing_date = db.Column(db.DateTime, nullable=True)
    auto_renew = db.Column(db.Boolean, default=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    canceled_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def computed_status(self) -> str:
        now = datetime.utcnow()
        status = self.status or "trialing"

        if status == "trialing" and self.trial_end:
            if now >= self.trial_end:
                if self.plan and self.plan.plan_type == "trial":
                    status = "expired"
                else:
                    status = "active"

        if (
            status in {"trialing", "active"}
            and self.cancel_at_period_end
            and self.current_period_end
        ):
            if now >= self.current_period_end:
                status = "canceled"

        if status == "active" and self.current_period_end and not self.auto_renew:
            if now >= self.current_period_end:
                status = "expired"

        if self.canceled_at and status not in {"expired", "canceled"}:
            status = "canceled"

        return status

    @property
    def is_trial(self) -> bool:
        return self.computed_status == "trialing"

    @property
    def is_active(self) -> bool:
        return self.computed_status in {"trialing", "active"}

    def to_dict(self):
        return {
            "id": self.id,
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.computed_status,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "current_period_start": self.current_period_start.isoformat()
            if self.current_period_start
            else None,
            "current_period_end": self.current_period_end.isoformat()
            if self.current_period_end
            else None,
            "next_billing_date": self.next_billing_date.isoformat()
            if self.next_billing_date
            else None,
            "auto_renew": self.auto_renew,
            "cancel_at_period_end": self.cancel_at_period_end,
            "canceled_at": self.canceled_at.isoformat() if self.canceled_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Lead(Base, db.Model):
    __tablename__ = "lead"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    company = db.Column(db.String(150))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="new")
    source = db.Column(db.String(120))
    details = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "company": self.company,
            "message": self.message,
            "status": self.status,
            "source": self.source,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentSettings(Base, db.Model):
    __tablename__ = "payment_settings"

    id = db.Column(db.Integer, primary_key=True)
    payment_address = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @classmethod
    def get_solo(cls):
        """Return the singleton payment settings row, creating it if missing."""
        instance = cls.query.get(1)
        if instance:
            return instance
        instance = cls(id=1)
        db.session.add(instance)
        db.session.commit()
        return instance

    def to_dict(self) -> dict[str, object]:
        return {
            "payment_address": self.payment_address or "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    details = db.Column(db.Text, nullable=True)

    user = db.relationship("User", backref="audit_logs")


def get_model_by_id(model_cls, identity, *, coerce_fn=int):
    """Safely fetch a model instance by id with optional coercion."""
    if identity is None:
        return None
    normalized_id = identity
    if coerce_fn:
        try:
            normalized_id = coerce_fn(identity)
        except Exception:
            normalized_id = identity
    if normalized_id in {None, ""}:
        return None
    return db.session.get(model_cls, normalized_id)


@login_manager.user_loader
def load_user(user_id: str):
    # The primary key for User is a UUID in current schema, but some older
    # deployments (or legacy data) may still contain integer IDs. Be tolerant
    # when loading by trying UUID first, falling back to int, and returning
    # None on any error so Flask-Login doesn't raise an exception which can
    # manifest as a 500 during request processing.
    try:
        import uuid as _uuid

        try:
            uid = _uuid.UUID(user_id)
            return db.session.get(User, uid)
        except Exception:
            # Not a UUID string; try integer ID
            try:
                return db.session.get(User, int(user_id))
            except Exception:
                return None
    except Exception:
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None


# Decorators for role enforcement
def requires_role(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)  # Forbidden
            # Compare role in a tolerant way: support Enum members and strings
            user_role = getattr(current_user, "role", None)
            role_value = getattr(user_role, "value", user_role)
            if role_value != required_role:
                abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator

def requires_any_role(allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)  # Forbidden
            user_role = getattr(current_user, "role", None)
            role_value = getattr(user_role, "value", user_role)
            if role_value not in allowed_roles:
                abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator
