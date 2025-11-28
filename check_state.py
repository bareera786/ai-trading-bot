#!/usr/bin/env python3
import json
from ai_ml_auto_bot_final import ultimate_trader, optimized_trader

print('ultimate_trader.trading_enabled:', ultimate_trader.trading_enabled)
print('optimized_trader.trading_enabled:', optimized_trader.trading_enabled)

with open('bot_persistence/bot_state.json', 'r') as f:
    state = json.load(f)
print('state file trading_enabled:', state['trader_state']['trading_enabled'])