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
        if current_user.is_admin:
            return jsonify({"error": "User access only"}), 403
        return func(*args, **kwargs)

    return wrapper
