"""Public marketing/landing routes."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, url_for
print(">>> MARKETING MODULE LOADED <<<")
from flask_login import current_user


from app.routes.utils import marketing_analytics_context

marketing_bp = Blueprint("marketing", __name__, url_prefix="")


@marketing_bp.route("/marketing", endpoint="marketing_landing")
def marketing_landing():
    version_label = current_app.config.get("VERSION_LABEL", "Ultimate AI Bot")
    return render_template(
        "marketing/landing.html",
        version_label=version_label,
        analytics=marketing_analytics_context(),
    )


@marketing_bp.route("/", endpoint="index")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))
    version_label = current_app.config.get("VERSION_LABEL", "Ultimate AI Bot")
    return render_template(
        "marketing/landing.html",
        version_label=version_label,
        analytics=marketing_analytics_context(),
    )


@marketing_bp.route("/pricing", endpoint="pricing")
def pricing():
    """Public pricing page showing available subscription plans."""
    version_label = current_app.config.get("VERSION_LABEL", "Ultimate AI Bot")
    return render_template(
        "marketing/pricing.html",
        version_label=version_label,
        analytics=marketing_analytics_context(),
    )
