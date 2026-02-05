from app import create_app
from app.models import Trade, SystemTrade
from app.extensions import db

app = create_app()
with app.app_context():
    print("--- User Trades ---")
    trades = Trade.query.all()
    if not trades:
        print("No User Trades found.")
    else:
        for t in trades:
            print(f"ID: {t.id} | Symbol: {t.symbol} | Type: {t.type} | Qty: {t.quantity} | User: {t.user_id}")

    print("\n--- System Trades ---")
    sys_trades = SystemTrade.query.all()
    if not sys_trades:
        print("No System Trades found.")
    else:
        for t in sys_trades:
            print(f"ID: {t.id} | Symbol: {t.symbol} | Type: {t.type} | Qty: {t.quantity} | User: {t.user_id}")
