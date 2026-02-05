
import os
import json
import logging
from datetime import datetime

# Setup environment
os.environ["SKIP_RUNTIME_BOOTSTRAP"] = "1"

from app import create_app
from app.extensions import db
from app.models import User, UserTrade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_trades")

def migrate_trades():
    app = create_app()
    with app.app_context():
        # Check if we have users
        user = User.query.first()
        if not user:
            logger.info("No users found. Creating default admin user...")
            from werkzeug.security import generate_password_hash
            user = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
                is_admin=True,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created default admin user (ID: {user.id})")

        # Check if trades already exist in SQL
        if UserTrade.query.count() > 0:
            logger.info(f"UserTrade table already has {UserTrade.query.count()} records. Skipping migration.")
            return

        # Path to trades.json
        # app/services/pathing might be complex, assume default relative path
        json_path = os.path.join("bot_persistence", "default", "trades.json")
        if not os.path.exists(json_path):
            # Try legacy path
            json_path = "trades.json"
        
        if not os.path.exists(json_path):
            logger.info("No trades.json found to migrate.")
            return

        logger.info(f"Found trades.json at {json_path}. Migrating...")
        
        try:
            with open(json_path, 'r') as f:
                trades_data = json.load(f)
            
            count = 0
            for t in trades_data:
                # Map fields
                # Handle timestamp safely
                ts_str = t.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.utcnow()
                else:
                    ts = datetime.utcnow()

                ut = UserTrade(
                    user_id=user.id,
                    symbol=t.get("symbol"),
                    side=t.get("side"),
                    quantity=safe_float(t.get("quantity")),
                    entry_price=safe_float(t.get("entry_price") or t.get("price")),
                    pnl=safe_float(t.get("pnl")),
                    status=t.get("status", "closed"),
                    signal_source=t.get("strategy"),
                    confidence_score=safe_float(t.get("confidence")),
                    timestamp=ts,
                    is_paper=t.get("execution_mode", "paper") != "real",
                    exchange="binance_spot" if t.get("execution_mode") == "real" else "paper",
                    reason=t.get("reason"),
                    details=t.get("details"),
                    order_id=t.get("real_order_id") or t.get("binance_order_id") or f"migrated_{t.get('trade_id')}_{count}"
                )
                db.session.add(ut)
                count += 1
            
            db.session.commit()
            logger.info(f"Successfully migrated {count} trades to SQL.")
            
            # Rename file
            # os.rename(json_path, json_path + ".migrated")
            # logger.info(f"Renamed {json_path} to {json_path}.migrated")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()

def safe_float(v):
    if v is None: return 0.0
    try:
        return float(v)
    except:
        return 0.0

if __name__ == "__main__":
    migrate_trades()
