"""Subscription helper utilities and services."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.extensions import db
from app.models import SubscriptionPlan, UserSubscription

# Default plan definitions used when seeding new deployments
DEFAULT_SUBSCRIPTION_PLAN_DEFINITIONS = [
    {
        'name': '14 Day Trial',
        'code': 'trial-14-day',
        'plan_type': 'trial',
        'price_usd': 0,
        'currency': 'USD',
        'duration_days': 14,
        'trial_days': 0,
        'description': 'Complimentary trial access for new tenants',
        'is_active': True,
        'is_featured': False,
    },
    {
        'name': 'Pro Monthly',
        'code': 'pro-monthly',
        'plan_type': 'monthly',
        'price_usd': 149,
        'currency': 'USD',
        'duration_days': 30,
        'trial_days': 7,
        'description': 'Full platform access billed every month',
        'is_active': True,
        'is_featured': True,
    },
    {
        'name': 'Pro Yearly',
        'code': 'pro-yearly',
        'plan_type': 'yearly',
        'price_usd': 1490,
        'currency': 'USD',
        'duration_days': 365,
        'trial_days': 14,
        'description': 'Yearly commitment with two months free',
        'is_active': True,
        'is_featured': False,
    },
]

ALLOWED_SUBSCRIPTION_PLAN_TYPES = {'trial', 'monthly', 'yearly', 'lifetime'}


def normalize_plan_code(raw_code: Optional[str]) -> str:
    """Normalize plan codes for uniqueness checks and references."""
    raw = (raw_code or '').strip().lower()
    if not raw:
        return ''
    sanitized = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '-' for ch in raw)
    sanitized = sanitized.strip('-')
    return sanitized or raw


def coerce_decimal(value, *, default=0):
    try:
        quantized = Decimal(str(value if value is not None else default))
    except Exception as exc:  # pragma: no cover - validation path
        raise ValueError('price_usd must be a valid number') from exc
    return quantized.quantize(Decimal('0.01'))


def coerce_bool(value, *, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def ensure_default_subscription_plans():
    """Seed the database with default subscription plans if missing."""
    try:
        created = 0
        for plan_data in DEFAULT_SUBSCRIPTION_PLAN_DEFINITIONS:
            code = plan_data['code']
            existing = SubscriptionPlan.query.filter_by(code=code).first()
            if not existing:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
                created += 1
            else:
                for field, value in plan_data.items():
                    setattr(existing, field, value)
        if created or DEFAULT_SUBSCRIPTION_PLAN_DEFINITIONS:
            db.session.commit()
            if created:
                print(f"✅ Seeded {created} default subscription plan(s)")
    except Exception as exc:  # pragma: no cover - seeding best-effort
        db.session.rollback()
        print(f"⚠️ Failed to seed subscription plans: {exc}")


def serialize_subscription(subscription):
    if not subscription:
        return {
            'status': 'inactive',
            'is_active': False,
            'is_trial': False,
            'plan': None,
        }
    data = subscription.to_dict()
    data.update(
        {
            'is_active': subscription.is_active,
            'is_trial': subscription.is_trial,
        }
    )
    if subscription.plan:
        data['plan_name'] = subscription.plan.name
        data['plan_code'] = subscription.plan.code
        data['plan_type'] = subscription.plan.plan_type
    return data


def cancel_user_subscription(user, immediate=False, reason=None):
    """Cancel the user's active subscription."""
    if not user or not user.active_subscription:
        return None

    subscription = user.active_subscription
    now = datetime.utcnow()
    if immediate:
        subscription.status = 'canceled'
        subscription.canceled_at = now
        subscription.cancel_at_period_end = False
    else:
        subscription.cancel_at_period_end = True

    if reason:
        note = f"{now.isoformat()}: {reason}"
        subscription.notes = f"{subscription.notes}\n{note}" if subscription.notes else note

    db.session.commit()
    return subscription


def assign_subscription_to_user(
    user,
    plan,
    *,
    trial_days=None,
    auto_renew=True,
    cancel_existing=True,
    notes=None,
):
    """Assign or upgrade a user's subscription to a particular plan."""
    if not user or not plan:
        raise ValueError('User and plan are required')

    now = datetime.utcnow()
    if cancel_existing and user.active_subscription:
        cancel_user_subscription(user, immediate=True, reason='Replaced with new plan')

    plan_duration = max(1, plan.duration_days or 30)
    effective_trial_days = plan.trial_days if trial_days is None else max(0, int(trial_days))
    trial_end = None
    current_period_start = now
    current_period_end = now + timedelta(days=plan_duration)
    next_billing_date = None
    normalized_plan_type = (plan.plan_type or 'monthly').lower()
    status = 'active'

    if normalized_plan_type == 'trial':
        status = 'trialing'
        trial_end = now + timedelta(days=plan_duration)
        current_period_end = trial_end
        auto_renew = False
    else:
        if effective_trial_days:
            trial_end = now + timedelta(days=effective_trial_days)
            current_period_start = trial_end
        else:
            current_period_start = now
        current_period_end = current_period_start + timedelta(days=plan_duration)
        next_billing_date = trial_end if trial_end else current_period_start
        status = 'trialing' if trial_end else 'active'

    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        status=status,
        trial_end=trial_end,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        next_billing_date=next_billing_date,
        auto_renew=auto_renew if normalized_plan_type != 'trial' else False,
        cancel_at_period_end=False,
        notes=notes,
    )
    db.session.add(subscription)
    db.session.commit()
    return subscription
