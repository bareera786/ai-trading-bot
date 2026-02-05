
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import CopyRelationship, User
from app.extensions import db
import random

copy_trading_bp = Blueprint('copy_trading', __name__, url_prefix='/copy-trading')

def get_mock_traders():
    """Generate fake consistent data for leaderboard demo."""
    names = ["AlexCrypto", "SatoshiNakamoto", "WhaleHunter", "ElonTusk", "DiamondHands"]
    traders = []
    for i, name in enumerate(names):
        # Deterministic random stats based on name length
        random.seed(len(name))
        roi = random.uniform(50, 500)
        win_rate = random.uniform(60, 95)
        copiers = int(random.uniform(100, 5000))
        
        traders.append({
            "id": i + 999, # Fake ID, in real app query User
            "username": name,
            "roi": round(roi, 2),
            "win_rate": round(win_rate, 1),
            "pnl": round(roi * 150, 2),
            "copiers": copiers,
            "risk_score": random.randint(1, 10),
            "is_following": False
        })
    # Sort by ROI
    traders.sort(key=lambda x: x['roi'], reverse=True)
    return traders

@copy_trading_bp.route('/')
@login_required
def leaderboard():
    """Copy Trading Leaderboard."""
    traders = get_mock_traders()
    
    # Check if user is actually following anyone (Real DB check)
    following_ids = [r.leader_id for r in current_user.following if r.is_active]
    
    # Check DB for relationships (for real users) or just mock for loop
    # For this demo, we can't easily join mock IDs with real DB. 
    # We will just pass the mock list.
    
    return render_template('copy_trading/leaderboard.html', traders=traders)

@copy_trading_bp.route('/follow/<int:trader_id>', methods=['POST'])
@login_required
def follow_trader(trader_id):
    """Action to follow a trader (Mock implementation)."""
    # In real world: find User by ID, create relationship
    # For Demo: Just flash success
    flash(f"Successfully started copying Trader #{trader_id}!", "success")
    return redirect(url_for('copy_trading.leaderboard'))
