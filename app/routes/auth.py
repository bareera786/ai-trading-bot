"""Clean, simple authentication routes."""
from __future__ import annotations

import logging
from typing import Optional

from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
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


@auth_bp.route("/login", methods=["GET", "POST"], strict_slashes=False)
@auth_bp.route("/login/", methods=["GET", "POST"], strict_slashes=False)
def login():
    """Handle login via form or JSON payload."""
    if current_user.is_authenticated:
        if request.is_json:
            return jsonify({"success": True, "message": "Already authenticated"}), 200
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        try:
            if request.is_json:
                data = request.get_json()
                username = data.get("username")
                password = data.get("password")
                remember = data.get("remember", False)
            else:
                username = request.form.get("username")
                password = request.form.get("password")
                remember = request.form.get("remember", False)

            # Validate required fields
            if not username or not password:
                error_message = "Username and password are required"
                if request.is_json:
                    return jsonify({"error": error_message}), 400
                flash(error_message)
                return render_template("auth/login.html")

            # Find user
            user = User.query.filter_by(username=username).first()
            
            if not user:
                logger.warning(f"Login attempt with non-existent user: {username}")
                error_message = "Invalid username or password"
                if request.is_json:
                    return jsonify({"error": error_message}), 401
                flash(error_message)
                return render_template("auth/login.html")

            # Check password
            if not user.check_password(password):
                logger.warning(f"Failed password attempt for user: {username}")
                error_message = "Invalid username or password"
                if request.is_json:
                    return jsonify({"error": error_message}), 401
                flash(error_message)
                return render_template("auth/login.html")

            # Check if user is active
            if not user.is_active:
                error_message = "Account is deactivated"
                if request.is_json:
                    return jsonify({"error": error_message}), 403
                flash(error_message)
                return render_template("auth/login.html")

            # Login user with Flask-Login
            login_user(user, remember=bool(remember))
            
            # Log successful login
            logger.info(f"User logged in successfully: {username} (remember={remember})")
            
            # Set session parameters
            session.permanent = True
            
            if request.is_json:
                response_data = {
                    "success": True, 
                    "message": "Login successful",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                }
                response = jsonify(response_data)
                # Set CORS headers
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                return response, 200
                
            return redirect(url_for("dashboard_bp.dashboard"))
            
        except Exception as e:
            logger.exception(f"Login error: {str(e)}")
            error_message = "Authentication error. Please try again."
            if request.is_json:
                return jsonify({"error": error_message}), 500
            flash(error_message)
            return render_template("auth/login.html")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"], strict_slashes=False)
@auth_bp.route("/register/", methods=["GET", "POST"], strict_slashes=False)
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

    return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["GET", "POST"], strict_slashes=False)
@auth_bp.route("/logout/", methods=["GET", "POST"], strict_slashes=False)
@login_required
def logout():
    """Handle user logout for both browser and API clients."""
    username = current_user.username if current_user.is_authenticated else "unknown"
    
    # Log before logout to ensure we capture the username
    logger.info(f"Logging out user: {username}")
    
    # Perform logout
    logout_user()
    
    # Clear session data
    try:
        session.clear()
        # Explicitly remove session cookie
        response = make_response()
        response.delete_cookie('session')
        response.delete_cookie('remember_token')
    except Exception as e:
        logger.exception(f"Error clearing session: {str(e)}")
    
    logger.info(f"User logged out successfully: {username}")
    
    # Check if client expects JSON response
    if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
        resp = jsonify({"success": True, "message": "Logged out successfully"})
        # Clear cookies in response
        resp.set_cookie('session', '', expires=0, httponly=True, samesite='None', secure=True)
        resp.set_cookie('remember_token', '', expires=0, httponly=True, samesite='None', secure=True)
        resp.headers.add('Access-Control-Allow-Credentials', 'true')
        return resp, 200
    
    # For browser requests, redirect to login
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

    try:
        user = User.query.filter_by(username=username).first()
    except Exception:
        logger.exception("API login query failed for user: %s", username)
        return jsonify({"error": "Authentication temporarily unavailable"}), 503

    password_ok = False
    if user and getattr(user, "password_hash", None):
        try:
            password_ok = user.check_password(password)
        except Exception:
            logger.exception("API password check failed for user: %s", username)
            password_ok = False

    if user and password_ok and user.is_active:
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


@auth_bp.route("/auth/status", methods=["GET"])
def auth_status():
    """Check authentication status."""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        }), 200
    return jsonify({"authenticated": False}), 200
