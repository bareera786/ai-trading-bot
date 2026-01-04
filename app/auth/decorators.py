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
        if not current_user.is_admin:
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
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Please login first"}), 401
        if getattr(current_user, "is_admin", False):
            return func(*args, **kwargs)

        subscription = getattr(current_user, "active_subscription", None)
        if subscription and getattr(subscription, "is_active", False):
            return func(*args, **kwargs)

        # Backward-compatible fallback: some deployments gate premium features
        # via a boolean property.
        if getattr(current_user, "is_premium", False):
            return func(*args, **kwargs)

        return jsonify({"error": "Active subscription required"}), 403

    return wrapper
