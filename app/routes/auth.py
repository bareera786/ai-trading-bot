"""Clean, simple authentication routes."""
from __future__ import annotations

import logging
from typing import Optional

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
    session,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle login via form or JSON payload."""
    if current_user.is_authenticated:
        if request.is_json:
            return jsonify({"success": True, "message": "Already authenticated"}), 200
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
        else:
            username = request.form.get("username")
            password = request.form.get("password")

        # Validate required fields
        if not username or not password:
            error_message = "Username and password are required"
            if request.is_json:
                return jsonify({"error": error_message}), 400
            flash(error_message)
            return render_template("auth/auth.html")

        # Find user
        user = User.query.filter_by(username=username).first()

        # Check credentials
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            logger.info(f"User logged in: {username}")

            if request.is_json:
                return jsonify({"success": True, "message": "Login successful"}), 200
            return redirect(url_for("dashboard_bp.dashboard"))

        # Invalid credentials
        error_message = "Invalid username or password"
        if request.is_json:
            return jsonify({"error": error_message}), 401
        flash(error_message)
        return render_template("auth/auth.html")

    return render_template("auth/auth.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Basic validation
        if not username or not email or not password:
            flash("All fields are required")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("auth.register"))

        # Check for existing users
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("auth.register"))

        # Create user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        logger.info(f"New user registered: {username} ({email})")

        flash("Registration successful! You can now log in.")
        return redirect(url_for("auth.login"))

    return render_template("auth/auth.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    """Handle user logout for both browser and API clients."""
    username = current_user.username if current_user.is_authenticated else "unknown"
    logout_user()
    # Ensure all session data is cleared to fully end the user's session
    try:
        session.clear()
    except Exception:
        # Be conservative: don't crash logout if session clearing fails
        logger.exception("Failed to clear session during logout")
    logger.info(f"User logged out: {username}")
    
    # Check if client expects JSON response
    if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({"success": True, "message": "Logged out"}), 200
    
    return redirect(url_for("auth.login"))


# API endpoints for programmatic access
@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    """API endpoint for user registration."""
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    # Check for existing users
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create user
    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    logger.info(f"New user registered via API: {username} ({email})")

    return jsonify({"success": True, "message": "Registration successful"}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """API endpoint for user login."""
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password) and user.is_active:
        login_user(user)
        logger.info(f"User logged in via API: {username}")
        return jsonify({"success": True, "message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/api/auth/logout", methods=["GET", "POST"])
@login_required
def api_logout():
    """API endpoint for user logout."""
    username = current_user.username if current_user.is_authenticated else "unknown"
    logout_user()
    # Ensure session is cleared for API clients as well
    try:
        session.clear()
    except Exception:
        logger.exception("Failed to clear session during API logout")
    logger.info(f"User logged out via API: {username}")
    return jsonify({"success": True, "message": "Logout successful"}), 200
