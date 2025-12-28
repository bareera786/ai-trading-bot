"""Public marketing/landing routes."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, url_for
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


@marketing_bp.route("/", endpoint="root_entry")
def root_entry():
    show_landing = current_app.config.get("SHOW_PUBLIC_LANDING", True)
    if current_user.is_authenticated or not show_landing:
        return redirect(url_for("dashboard_bp.dashboard"))
    return redirect(url_for("marketing.marketing_landing"))
