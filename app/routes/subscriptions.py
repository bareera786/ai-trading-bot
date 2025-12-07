"""Blueprint containing subscription management endpoints."""
from __future__ import annotations

from datetime import datetime
from time import time

from flask import Blueprint, current_app, jsonify, request

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import SubscriptionPlan, User
from app.subscriptions.helpers import (
    ALLOWED_SUBSCRIPTION_PLAN_TYPES,
    assign_subscription_to_user,
    cancel_user_subscription,
    coerce_bool,
    coerce_decimal,
    normalize_plan_code,
    serialize_subscription,
)

subscription_bp = Blueprint('subscriptions', __name__, url_prefix='/api')

_PUBLIC_PLAN_CACHE: dict[str, object] = {
    'payload': None,
    'expires_at': 0.0,
}


def _invalidate_public_plan_cache() -> None:
    _PUBLIC_PLAN_CACHE['payload'] = None
    _PUBLIC_PLAN_CACHE['expires_at'] = 0.0


def _apply_featured_flag(plan: SubscriptionPlan, should_feature: bool) -> None:
    if plan is None:
        return
    if plan.id is None:
        db.session.flush()
    if should_feature:
        SubscriptionPlan.query.filter(SubscriptionPlan.id != plan.id).update(
            {SubscriptionPlan.is_featured: False}, synchronize_session=False
        )
        plan.is_featured = True
    else:
        plan.is_featured = False


def _build_public_plan_payload() -> dict[str, object]:
    plans = (
        SubscriptionPlan.query.filter_by(is_active=True)
        .order_by(SubscriptionPlan.price_usd.asc())
        .all()
    )
    featured_plan = next((plan for plan in plans if plan.is_featured), plans[0] if plans else None)
    return {
        'plans': [plan.to_dict() for plan in plans],
        'featured_plan': featured_plan.to_dict() if featured_plan else None,
        'retrieved_at': datetime.utcnow().isoformat() + 'Z',
    }


@subscription_bp.route('/subscriptions/plans', methods=['GET'])
def api_public_subscription_plans():
    try:
        ttl = int(current_app.config.get('PUBLIC_SUBSCRIPTION_CACHE_SECONDS', 120))
    except (TypeError, ValueError):  # pragma: no cover - defensive
        ttl = 120

    now = time()
    cached = _PUBLIC_PLAN_CACHE['payload']
    expires_at = float(_PUBLIC_PLAN_CACHE['expires_at'] or 0)
    if cached and now < expires_at:
        return jsonify(cached)

    try:
        payload = _build_public_plan_payload()
        _PUBLIC_PLAN_CACHE['payload'] = payload
        _PUBLIC_PLAN_CACHE['expires_at'] = now + max(5, ttl)
        return jsonify(payload)
    except Exception as exc:
        print(f"Error in GET /api/subscriptions/plans: {exc}")
        return jsonify({'error': 'Unable to load subscription plans'}), 500


@subscription_bp.route('/admin/subscription/plans', methods=['GET'])
@admin_required
def api_list_subscription_plans():
    try:
        plans = SubscriptionPlan.query.order_by(
            SubscriptionPlan.is_active.desc(),
            SubscriptionPlan.price_usd.asc(),
        ).all()
        return jsonify({'plans': [plan.to_dict() for plan in plans], 'count': len(plans)})
    except Exception as exc:
        print(f"Error in GET /api/admin/subscription/plans: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/admin/subscription/plans', methods=['POST'])
@admin_required
def api_create_subscription_plan():
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        code = normalize_plan_code(data.get('code'))
        plan_type = (data.get('plan_type') or 'monthly').strip().lower()
        duration_days = int(data.get('duration_days') or 0)
        trial_days = int(data.get('trial_days') or 0)
        description = (data.get('description') or '').strip() or None
        currency = (data.get('currency') or 'USD').strip().upper()
        is_featured = coerce_bool(data.get('is_featured'), default=False)

        if not name:
            return jsonify({'error': 'name is required'}), 400
        if not code:
            return jsonify({'error': 'code is required'}), 400
        if plan_type not in ALLOWED_SUBSCRIPTION_PLAN_TYPES:
            return jsonify({'error': f'plan_type must be one of {sorted(ALLOWED_SUBSCRIPTION_PLAN_TYPES)}'}), 400
        if duration_days <= 0:
            return jsonify({'error': 'duration_days must be greater than zero'}), 400
        if trial_days < 0:
            return jsonify({'error': 'trial_days cannot be negative'}), 400

        price_usd = coerce_decimal(data.get('price_usd', 0))

        existing_code = SubscriptionPlan.query.filter_by(code=code).first()
        if existing_code:
            return jsonify({'error': 'A subscription plan with this code already exists'}), 400

        plan = SubscriptionPlan(
            name=name,
            code=code,
            plan_type=plan_type,
            price_usd=price_usd,
            currency=currency,
            duration_days=duration_days,
            trial_days=trial_days,
            description=description,
            is_active=coerce_bool(data.get('is_active'), default=True),
            is_featured=is_featured,
        )
        db.session.add(plan)
        _apply_featured_flag(plan, is_featured)
        db.session.commit()
        _invalidate_public_plan_cache()

        return jsonify({'success': True, 'plan': plan.to_dict()}), 201
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as exc:
        db.session.rollback()
        print(f"Error in POST /api/admin/subscription/plans: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/admin/subscription/plans/<int:plan_id>', methods=['PUT'])
@admin_required
def api_update_subscription_plan(plan_id):
    try:
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            return jsonify({'error': 'Subscription plan not found'}), 404

        data = request.get_json() or {}
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'error': 'name cannot be empty'}), 400
            plan.name = name

        if 'code' in data:
            new_code = normalize_plan_code(data.get('code'))
            if not new_code:
                return jsonify({'error': 'code cannot be empty'}), 400
            existing = SubscriptionPlan.query.filter(
                SubscriptionPlan.code == new_code,
                SubscriptionPlan.id != plan.id,
            ).first()
            if existing:
                return jsonify({'error': 'Another plan already uses this code'}), 400
            plan.code = new_code

        if 'plan_type' in data:
            plan_type = (data.get('plan_type') or '').strip().lower()
            if plan_type not in ALLOWED_SUBSCRIPTION_PLAN_TYPES:
                return jsonify({'error': f'plan_type must be one of {sorted(ALLOWED_SUBSCRIPTION_PLAN_TYPES)}'}), 400
            plan.plan_type = plan_type

        if 'duration_days' in data:
            duration_days = int(data.get('duration_days') or 0)
            if duration_days <= 0:
                return jsonify({'error': 'duration_days must be greater than zero'}), 400
            plan.duration_days = duration_days

        if 'trial_days' in data:
            trial_days = int(data.get('trial_days') or 0)
            if trial_days < 0:
                return jsonify({'error': 'trial_days cannot be negative'}), 400
            plan.trial_days = trial_days

        if 'price_usd' in data:
            plan.price_usd = coerce_decimal(data.get('price_usd'))

        if 'currency' in data:
            plan.currency = (data.get('currency') or 'USD').strip().upper()

        if 'description' in data:
            plan.description = (data.get('description') or '').strip() or None

        if 'is_active' in data:
            plan.is_active = coerce_bool(data.get('is_active'), default=plan.is_active)

        if 'is_featured' in data:
            should_feature = coerce_bool(data.get('is_featured'), default=plan.is_featured)
            _apply_featured_flag(plan, should_feature)

        db.session.commit()
        _invalidate_public_plan_cache()
        return jsonify({'success': True, 'plan': plan.to_dict()})
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as exc:
        db.session.rollback()
        print(f"Error in PUT /api/admin/subscription/plans/{plan_id}: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/admin/subscription/plans/<int:plan_id>/toggle', methods=['PATCH'])
@admin_required
def api_toggle_subscription_plan(plan_id):
    try:
        plan = db.session.get(SubscriptionPlan, plan_id)
        if not plan:
            return jsonify({'error': 'Subscription plan not found'}), 404

        data = request.get_json() or {}
        if 'is_active' in data:
            plan.is_active = coerce_bool(data.get('is_active'), default=plan.is_active)
        else:
            plan.is_active = not plan.is_active

        db.session.commit()
        _invalidate_public_plan_cache()
        return jsonify({'success': True, 'plan': plan.to_dict()})
    except Exception as exc:
        db.session.rollback()
        print(f"Error in PATCH /api/admin/subscription/plans/{plan_id}/toggle: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/users/<username>/subscription', methods=['GET'])
@admin_required
def api_get_user_subscription(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        subscription = serialize_subscription(user.active_subscription)
        active_plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.price_usd.asc()).all()
        return jsonify(
            {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'is_admin': user.is_admin,
                },
                'subscription': subscription,
                'available_plans': [plan.to_dict() for plan in active_plans],
            }
        )
    except Exception as exc:
        print(f"Error in GET /api/users/{username}/subscription: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/users/<username>/subscription', methods=['POST'])
@admin_required
def api_assign_user_subscription(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json() or {}
        plan_id = data.get('plan_id')
        plan_code = data.get('plan_code')
        notes = (data.get('notes') or '').strip() or None

        plan = None
        if plan_id:
            plan = db.session.get(SubscriptionPlan, plan_id)
        elif plan_code:
            plan = SubscriptionPlan.query.filter_by(code=normalize_plan_code(plan_code)).first()

        if not plan:
            return jsonify({'error': 'Subscription plan not found'}), 404
        if not plan.is_active:
            return jsonify({'error': 'Cannot assign an inactive plan'}), 400

        trial_days = data.get('trial_days')
        if trial_days is not None:
            try:
                trial_days = int(trial_days)
            except ValueError:
                return jsonify({'error': 'trial_days must be an integer'}), 400
            if trial_days < 0:
                return jsonify({'error': 'trial_days cannot be negative'}), 400

        auto_renew = coerce_bool(data.get('auto_renew'), default=(plan.plan_type != 'trial'))
        cancel_existing = coerce_bool(data.get('cancel_existing'), default=True)

        subscription = assign_subscription_to_user(
            user,
            plan,
            trial_days=trial_days,
            auto_renew=auto_renew,
            cancel_existing=cancel_existing,
            notes=notes,
        )

        return jsonify({'success': True, 'subscription': serialize_subscription(subscription)})
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as exc:
        db.session.rollback()
        print(f"Error in POST /api/users/{username}/subscription: {exc}")
        return jsonify({'error': str(exc)}), 500


@subscription_bp.route('/users/<username>/subscription', methods=['DELETE'])
@admin_required
def api_cancel_user_subscription(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.active_subscription:
            return jsonify({'error': 'User does not have an active subscription'}), 400

        data = request.get_json(silent=True) or {}
        params = request.args or {}

        immediate_source = data.get('immediate') if data else None
        if immediate_source is None:
            immediate_source = params.get('immediate')
        immediate = coerce_bool(immediate_source, default=False)
        reason = data.get('reason') or params.get('reason')

        subscription = cancel_user_subscription(user, immediate=immediate, reason=reason)
        if not subscription:
            return jsonify({'error': 'No active subscription to cancel'}), 400

        return jsonify({'success': True, 'subscription': serialize_subscription(subscription)})
    except Exception as exc:
        db.session.rollback()
        print(f"Error in DELETE /api/users/{username}/subscription: {exc}")
        return jsonify({'error': str(exc)}), 500
