import json
import os
import sys
from datetime import datetime

# Path to state file
STATE_FILE = "bot_persistence/default/bot_state.json"

def enable_trading():
    if not os.path.exists(STATE_FILE):
        print(f"Error: {STATE_FILE} not found.")
        return

    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

        print("Current State:")
        print(f"  Spot Enabled: {state['trader_state'].get('trading_enabled')}")
        print(f"  Futures Enabled: {state['trader_state'].get('futures_trading_enabled')}")
        
        # Enable Spot
        state['trader_state']['trading_enabled'] = True
        state['configuration']['TRADING_CONFIG']['auto_trade_enabled'] = True # Legacy/Config
        
        # Enable Futures
        state['trader_state']['futures_trading_enabled'] = True
        state['configuration']['TRADING_CONFIG']['futures_enabled'] = True
        state['configuration']['TRADING_CONFIG']['futures_manual_auto_trade'] = True
        
        # Futures Manual Settings
        if 'futures_manual_settings' in state:
            state['futures_manual_settings']['auto_trade_enabled'] = True
            
        # Update Timestamp
        state['timestamp'] = datetime.now().isoformat()
        
        # Save
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
            
        print("\nUpdated State:")
        print("  Spot Enabled: True")
        print("  Futures Enabled: True")
        print("  Futures Manual Auto-Trade: True")
        print(f"Successfully updated {STATE_FILE}")

    except Exception as e:
        print(f"Error updating state: {e}")

if __name__ == "__main__":
    enable_trading()
