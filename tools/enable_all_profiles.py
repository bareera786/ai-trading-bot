import json
import os
import glob
from datetime import datetime

# Path to persistence directory
PERSISTENCE_DIR = "bot_persistence"

def enable_trading_for_file(state_file):
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

        print(f"Processing: {state_file}")
        
        # Ensure structures exist
        if "trader_state" not in state: state["trader_state"] = {}
        if "configuration" not in state: state["configuration"] = {}
        if "TRADING_CONFIG" not in state["configuration"]: state["configuration"]["TRADING_CONFIG"] = {}
        if "futures_manual_settings" not in state: state["futures_manual_settings"] = {}

        # Enable Spot
        state['trader_state']['trading_enabled'] = True
        state['configuration']['TRADING_CONFIG']['auto_trade_enabled'] = True
        
        # Enable Futures
        state['trader_state']['futures_trading_enabled'] = True
        state['configuration']['TRADING_CONFIG']['futures_enabled'] = True
        state['configuration']['TRADING_CONFIG']['futures_manual_auto_trade'] = True
        
        # Futures Manual Settings
        state['futures_manual_settings']['auto_trade_enabled'] = True
            
        # Update Timestamp
        state['timestamp'] = datetime.now().isoformat()
        
        # Save
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        print(f"  -> Enabled Spot, Futures, and Manual Auto-Trade.")

    except Exception as e:
        print(f"  -> Error updating {state_file}: {e}")

def main():
    if not os.path.exists(PERSISTENCE_DIR):
        print(f"Error: {PERSISTENCE_DIR} not found.")
        return

    # Find all bot_state.json files (recursive)
    # 1. Default profile
    default_state = os.path.join(PERSISTENCE_DIR, "default", "bot_state.json")
    if os.path.exists(default_state):
        enable_trading_for_file(default_state)
    
    # 2. User profiles
    user_dirs = glob.glob(os.path.join(PERSISTENCE_DIR, "user_*"))
    for user_dir in user_dirs:
        user_state = os.path.join(user_dir, "bot_state.json")
        if os.path.exists(user_state):
            enable_trading_for_file(user_state)

    print("\nAll profiles updated.")

if __name__ == "__main__":
    main()
