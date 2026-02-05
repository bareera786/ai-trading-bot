import redis
import logging
import sys
import os
import json

# Ensure we can import app modules
sys.path.append(os.getcwd())

# MOCK ENVIRONMENT for local testing
os.environ["ENCRYPTION_KEY"] = "_w4w7_yRXTy1i_46yuUoTv_xIcXmpBs_dQPdJbnOB1U="
os.environ["FLASK_APP"] = "app"
os.environ["DATABASE_URL"] = "postgresql://trading_user:secure_password_123@localhost:5432/trading_bot" 
# NOTE: Local DB might not be reachable if inside docker. 
# But SignalPublisher only needs Redis.

from app.services.signal_publisher import SignalPublisher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_trading_bot")

def verify_metadata():
    print("🛡️ Verifying Signal Metadata Injection...")
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(redis_url, decode_responses=True)
    
    # 1. Setup Redis State
    print("\n1️⃣ Setting Active Model Version in Redis...")
    active_version = "v2.TEST_VERSION_123"
    r.set("brain:active_model_version", active_version)
    r.set("brain:signals:paused", "0") # Ensure not paused
    
    publisher = SignalPublisher(redis_conn=r)
    
    # 2. Publish Signal (No metadata)
    print("\n2️⃣ Publishing Signal (without explicit metadata)...")
    msg_id = publisher.publish_signal(
        symbol="BTCUSDT",
        side="LONG",
        confidence=0.95,
        price=50000.0
    )
    
    if not msg_id:
        print("❌ Failed to publish signal.")
        return False
        
    # 3. Read from Stream and Verify
    print("\n3️⃣ Verifying Stream Content...")
    # Read last message
    streams = r.xread({"trade_signals": "0-0"}, count=100, block=1000)
    # Find our message
    found = False
    for stream_name, messages in streams:
        for mid, data in messages:
            if mid == msg_id:
                found = True
                print(f"✅ Found message {mid}")
                metadata_str = data.get("metadata", "{}")
                metadata = json.loads(metadata_str)
                
                if metadata.get("model_version") == active_version:
                    print(f"✅ SUCCESS: Injected model_version = {metadata['model_version']}")
                else:
                    print(f"❌ FAIL: Expected {active_version}, got {metadata.get('model_version')}")
                    return False
    
    if not found:
        print("❌ Could not find published message in stream.")
        return False
        
    print("\n🛡️ Metadata Verification COMPLETE!")
    return True

if __name__ == "__main__":
    try:
        if verify_metadata():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        sys.exit(1)
