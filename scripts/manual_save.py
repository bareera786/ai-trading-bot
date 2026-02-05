#!/usr/bin/env python3
"""Manual save helper for debugging persistence permissions."""
from app import create_app

app = create_app()
with app.app_context():
    ctx = app.extensions.get('ai_bot_context', {})
    pm = ctx.get('persistence_manager')
    trader = ctx.get('ultimate_trader')
    ml = ctx.get('ultimate_ml_system')
    cfg = ctx.get('trading_config', {})
    symbols = ctx.get('top_symbols', [])
    hist = ctx.get('historical_data', {})
    print("persistence_manager available:", bool(pm))
    if pm:
        ok = pm.save_complete_state(trader, ml, cfg, symbols, hist)
        print('Manual save result:', ok)
    else:
        print('Persistence manager not present in context')
