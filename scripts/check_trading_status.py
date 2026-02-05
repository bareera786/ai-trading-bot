import os
import sys
import redis
import json

def check_status():
    print("--- Configuration Check (Environment Variables) ---")
    print(f"ENABLE_FUTURES_TRADING: {os.getenv('ENABLE_FUTURES_TRADING', 'Not Set')}")
    print(f"ENABLE_AUTO_TRADING: {os.getenv('ENABLE_AUTO_TRADING', 'Not Set')}")
    
    # Defaults known from code analysis
    futures_default = "0"
    auto_default = "0"
    
    futures_enabled = os.getenv("ENABLE_FUTURES_TRADING", futures_default).lower() in ("1", "true", "yes")
    auto_enabled = os.getenv("ENABLE_AUTO_TRADING", auto_default).lower() in ("1", "true", "yes")
    
    print(f"Effective Futures Enabled: {futures_enabled}")
    print(f"Effective Auto Trade Enabled: {auto_enabled}")
    
    global_lock = os.getenv("GLOBAL_TRADING_LOCK", "0").lower() in ("1", "true", "yes")
    print(f"Global Trading Lock (Kill Switch): {global_lock}")

    print("\n--- Redis State ---")
    try:
        r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', '6379')), decode_responses=True)
        settings_json = r.get("trading:settings")
        if settings_json:
            settings = json.loads(settings_json)
            print(f"Redis Trading Settings available: Yes")
            print(f"Redis 'trading_enabled': {settings.get('trading_enabled')}")
            print(f"Redis 'paper_trading': {settings.get('paper_trading')}")
        else:
            print("Redis key 'trading:settings' NOT FOUND")

        # Check dashboard global state for system status
        dashboard_msg = r.get("dashboard:global_state")
        if dashboard_msg:
             data = json.loads(dashboard_msg)
             sys_status = data.get("system_status", {})
             print(f"System Status: {sys_status}")
        else:
             print("Redis key 'dashboard:global_state' NOT FOUND")
            
    except Exception as e:
        print(f"Error connecting to Redis: {e}")

if __name__ == "__main__":
    check_status()
