import redis
import logging
import sys
import os

# Ensure we can import app modules
sys.path.append(os.getcwd())

# MOCK ENVIRONMENT for local testing
os.environ["ENCRYPTION_KEY"] = "_w4w7_yRXTy1i_46yuUoTv_xIcXmpBs_dQPdJbnOB1U="
os.environ["FLASK_APP"] = "app"

from app.services.signal_publisher import SignalPublisher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_trading_bot")

def verify_safety():
    print("🛡️ Verifying Signal Safety...")
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(redis_url, decode_responses=True)
    
    publisher = SignalPublisher(redis_conn=r)
    
    # 1. Test BLOCKED state
    print("\n1️⃣ Testing PAUSED state...")
    r.set("brain:signals:paused", "1")
    
    result = publisher.publish_signal(
        symbol="BTCUSDT",
        side="LONG",
        confidence=0.99,
        price=50000.0,
        signal_source="safety_check"
    )
    
    if result is None:
        print("✅ SUCCESS: Signal blocked when paused.")
    else:
        print(f"❌ FAILED: Signal published despite pause! ID: {result}")
        return False
        
    # 2. Test ACTIVE state
    print("\n2️⃣ Testing ACTIVE state...")
    r.set("brain:signals:paused", "0")
    
    # Clean stream first to avoid noise
    r.delete("trade_signals")
    
    result = publisher.publish_signal(
        symbol="BTCUSDT",
        side="LONG", 
        confidence=0.99,
        price=50000.0,
        signal_source="safety_check"
    )
    
    if result:
        print(f"✅ SUCCESS: Signal published when active. ID: {result}")
    else:
        print("❌ FAILED: Signal failed to publish when active.")
        return False
        
    print("\n🛡️ Signal Safety Verification COMPLETE!")
    return True

if __name__ == "__main__":
    try:
        if verify_safety():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        sys.exit(1)
