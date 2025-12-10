"""Authentication views blueprint."""
from __future__ import annotations

import logging

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.models import User
from app.routes.utils import marketing_analytics_context


auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
@limiter.limit("5 per minute")
def login():
    """Handle login via form or JSON payload."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    error_message = "Invalid username or password"
    active_tab = "login"

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
        else:
            username = request.form.get("username")
            password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"User {username} logged in successfully from IP {request.remote_addr}")
            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "message": "Login successful",
                        "user": {
                            "username": user.username,
                            "is_admin": user.is_admin,
                            "id": user.id,
                        },
                    }
                )
            next_page = request.args.get("next")
            response = (
                redirect(next_page)
                if next_page
                else redirect(url_for("dashboard_bp.dashboard"))
            )
            response.headers[
                "Cache-Control"
            ] = "no-cache, no-store, must-revalidate, max-age=0, private, no-transform"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

        logger.warning(f"Failed login attempt for username '{username}' from IP {request.remote_addr}")
        if request.is_json:
            return jsonify({"error": error_message}), 401

        flash(error_message)

    return render_template("auth/auth.html", analytics=marketing_analytics_context(), active_tab=active_tab)


@auth_bp.route("/logout", endpoint="logout")
@login_required
def logout():
    """Destroy the active session and redirect to login."""
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"], endpoint="register")
@limiter.limit("3 per minute")
def register():
    """Render or process the registration form."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    active_tab = "register"

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        captcha = request.form.get("captcha")

        if captcha != "7":
            flash("CAPTCHA verification failed")
            return redirect(url_for("auth.register"))

        if not email or "@" not in email or "." not in email:
            flash("Please enter a valid email address")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email, is_admin=False, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        logger.info(f"New user registered: {username} ({email}) from IP {request.remote_addr}")

        flash("Registration successful! Please login.")
        return redirect(url_for("auth.login"))

    return render_template("auth/auth.html", analytics=marketing_analytics_context(), active_tab=active_tab)
