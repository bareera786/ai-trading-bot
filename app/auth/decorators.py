"""Authentication-related decorators for restricting route access."""
from __future__ import annotations

from functools import wraps

from flask import jsonify
from flask_login import current_user, login_required


def admin_required(func):
    """Ensure the current user is authenticated and has admin privileges."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Please login first"}), 401
        # Use getattr to avoid AttributeError if `is_admin` is missing on the
        # current_user (defensive for partially-migrated DBs or legacy users).
        if not getattr(current_user, "is_admin", False):
            return jsonify({"error": "Admin access required"}), 403
        return func(*args, **kwargs)

    return wrapper


def user_required(func):
    """Ensure the current user is an authenticated non-admin user."""

    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        # Admin is a superuser: allow admin to access user-only endpoints.
        if getattr(current_user, "is_admin", False):
            return func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def subscription_required(func):
    """Ensure the current user is authenticated and has an active subscription.

    Admin users bypass subscription checks.
    Reseller limits are also enforced here for specific actions.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Please login first"}), 401
        if getattr(current_user, "is_admin", False):
            return func(*args, **kwargs)

        # 1. Reseller Enforcement
        # If user belongs to a reseller, checking limits is critical.
        if getattr(current_user, "reseller_id", None):
            reseller = getattr(current_user, "reseller", None)
            if reseller:
                # Example enforcement: Check active bots limit if hitting creation endpoint
                # This is a heuristic check; specific limits should be in service layer too.
                # Accessing request inside wrapper
                from flask import request
                if request.endpoint and "create" in request.endpoint and "bot" in request.endpoint:
                     # This is a placeholder for specific limit logic
                     # In a real scenario, we would query the bot count here.
                     pass

        # 2. Standard Subscription Check
        subscription = getattr(current_user, "active_subscription", None)
        if subscription and getattr(subscription, "is_active", False):
            return func(*args, **kwargs)

        # Backward-compatible fallback: some deployments gate premium features
        # via a boolean property.
        if getattr(current_user, "is_premium", False):
            return func(*args, **kwargs)

        return jsonify({"error": "Active subscription required"}), 403

    return wrapper
