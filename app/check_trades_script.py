from app import create_app
from app.models import UserTrade
from app.extensions import db

def check():
    app = create_app()
    with app.app_context():
        print("--- User Trades ---")
        trades = UserTrade.query.all()
        if not trades:
            print("No User Trades found.")
        else:
            for t in trades:
                print(f"ID: {t.id} | Symbol: {t.symbol} | Type: {t.trade_type} | Qty: {t.quantity} | User: {t.user_id} | Status: {t.status}")


if __name__ == "__main__":
    check()
