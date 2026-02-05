
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models import UserTrade, UserPortfolio, User, SystemSetting, UserSubscription, SubscriptionPlan  # Import to register models
print(f"DEBUG: UserTrade loaded from {UserTrade.__module__}")
try:
    import inspect
    print(f"DEBUG: UserTrade file: {inspect.getfile(UserTrade)}")
except:
    pass

def init_db():
    app = create_app()
    with app.app_context():
        print(f"DEBUG: Connecting to {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("Dropping all database tables...")
        db.drop_all()
        print("Creating all database tables...")
        db.create_all()
        print("Database initialized successfully.")
        
        # Verify UserTrade columns
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('user_trade')]
            print(f"UserTrade columns: {columns}")
            
            required = ['order_id', 'realized_pnl', 'trade_group_id', 'exchange']
            missing = [c for c in required if c not in columns]
            if missing:
                print(f"❌ Missing columns in user_trade: {missing}")
            else:
                print("✅ UserTrade schema verification passed.")

            # Verify SystemSetting columns
            columns_ss = [c['name'] for c in inspector.get_columns('system_setting')]
            print(f"SystemSetting columns: {columns_ss}")
            
            required_ss = ['key', 'value', 'updated_at', 'updated_by']
            missing_ss = [c for c in required_ss if c not in columns_ss]
            if missing_ss:
                print(f"❌ Missing columns in system_setting: {missing_ss}")
            else:
                print("✅ SystemSetting schema verification passed.")

        except Exception as e:
            print(f"Verification failed: {e}")

if __name__ == "__main__":
    init_db()
