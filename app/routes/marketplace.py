"""Marketplace routes for strategy sharing and copying."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import MarketplaceStrategy, UserPortfolio
from datetime import datetime

marketplace_bp = Blueprint("marketplace", __name__, url_prefix="/marketplace")

@marketplace_bp.route("/", methods=["GET"])
@login_required
def index():
    """Render the marketplace storefront."""
    # Fetch strategies
    strategies = MarketplaceStrategy.query.filter_by(is_public=True).order_by(MarketplaceStrategy.roi_30d.desc()).all()
    
    return render_template(
        "marketplace.html",
        strategies=strategies,
        current_time=datetime.utcnow().timestamp()
    )

@marketplace_bp.route("/copy/<int:strategy_id>", methods=["POST"])
@login_required
def copy_strategy(strategy_id):
    """Copy a strategy's parameters to the user's portfolio."""
    strategy = MarketplaceStrategy.query.get_or_404(strategy_id)
    
    # Logic to apply parameters (Mock for now, would integrate with StrategyManager)
    # 1. Update UserPortfolio or Strategy Config
    # 2. Log the copy action
    
    strategy.copiers_count += 1
    db.session.commit()
    
    flash(f"Successfully copied strategy: {strategy.name}", "success")
    return redirect(url_for("marketplace.index"))

@marketplace_bp.route("/publish", methods=["POST"])
@login_required
def publish_strategy():
    """Publish a new strategy (Stub)."""
    # Logic to create a new MarketplaceStrategy from user's current settings
    return jsonify({"success": False, "message": "Publishing implementation pending"})
