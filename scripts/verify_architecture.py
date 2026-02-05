import os
import sys
import redis
import time

# Configuration (Defaults for Docker Environment)
REDIS_URL = os.getenv("REDIS_URL", "redis://trading-bot-redis:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@trading-bot-postgres:5432/db") # Example

def verify_system():
    print("🔍 Verifying System Architecture (Lightweight)...\n")
    
    # 1. Redis Connection
    try:
        r = redis.from_url(REDIS_URL)
        if r.ping():
            print(f"✅ Redis: Connected to {REDIS_URL}")
            
            # 2. Kill Switch Status
            lock = r.get("global_trading_lock")
            if lock:
                print("⚠️  Global Kill Switch: ACTIVE (System Halted)")
            else:
                print("✅ Global Kill Switch: INACTIVE (System Running)")

            # 3. Stream Existence
            try:
                # xinfo_stream might fail if stream doesn't exist
                if r.exists("trade_signals"):
                    info = r.xinfo_stream("trade_signals")
                    print(f"✅ Redis Stream 'trade_signals': Exists (Length: {info['length']})")
                    
                    groups = r.xinfo_groups("trade_signals")
                    print(f"DEBUG: Groups raw: {groups}")
                    execution_group = next((g for g in groups if g["name"] == "execution_group" or g["name"] == b"execution_group"), None)
                    if execution_group:
                        print(f"✅ Consumer Group 'execution_group': Active (Consumers: {execution_group['consumers']})")
                    else:
                        print("❌ Consumer Group 'execution_group': MISSING")
                else:
                    print("⚠️  Redis Stream 'trade_signals': Does not exist yet (Normal if no signals)")
            except Exception as e:
                print(f"⚠️  Redis Stream Error: {e}")
                
    except Exception as e:
        print(f"❌ Redis: Failed ({e})")
        return

    print("\n🚀 Lightweight Verification Complete.")

if __name__ == "__main__":
    verify_system()
