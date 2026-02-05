
import os
import sys
import logging
from datetime import datetime, timedelta

# Ensure we can import app modules
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
import app.extensions as extensions
from app.models import MLModel, SystemSetting
from app.core.config_trading import TRADING_CONFIG
from app.runtime.symbols import get_active_trading_universe

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("system_health")

def check_redis():
    try:
        if extensions.redis_client and extensions.redis_client.ping():
            logger.info("✅ Redis connection: OK")
            return True
        else:
            logger.error("❌ Redis connection failed: Client is None or ping failed")
            return False
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

def check_database():
    try:
        # Simple query to check DB
        count = MLModel.query.count()
        logger.info(f"✅ Database connection: OK (Found {count} models)")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_brain_status():
    if not extensions.redis_client:
        return
    
    # 1. Check Pause status
    paused_val = extensions.redis_client.get("brain:signals:paused")
    is_paused = False
    if paused_val:
         is_paused = (paused_val.decode() == "1") if isinstance(paused_val, bytes) else (paused_val == "1")
    
    if is_paused:
        logger.warning("⚠️  BRAIN IS PAUSED (Kill Switch Active)")
    else:
        logger.info("✅ Brain Signals: ACTIVE")

    # 2. Check Heartbeat
    last_beat = extensions.redis_client.get("brain:heartbeat")
    if last_beat:
        try:
            last_ts = float(last_beat)
            age = datetime.utcnow().timestamp() - last_ts
            if age < 120:
                logger.info(f"✅ Inference Heartbeat: OK (Last beat {age:.1f}s ago)")
            else:
                logger.error(f"❌ Inference Heartbeat: STALLED (Last beat {age:.1f}s ago)")
        except:
            logger.warning(f"⚠️  Invalid heartbeat value: {last_beat}")
    else:
        logger.error("❌ Inference Heartbeat: MISSING")

def check_active_models():
    active_models = MLModel.query.filter_by(status="active").all()
    if not active_models:
        logger.error("❌ No ACTIVE models found in database!")
    else:
        for m in active_models:
            logger.info(f"✅ Active Model: {m.version} (Strategy: {m.strategy.name if m.strategy else 'Legacy'})")
            
def check_trading_config():
    logger.info("--- Trading Config ---")
    logger.info(f"Auto Trade Enabled: {TRADING_CONFIG.get('auto_trade_enabled')}")
    logger.info(f"Futures Enabled: {TRADING_CONFIG.get('futures_enabled')}")
    
    universe = get_active_trading_universe()
    if not universe:
        logger.error("❌ Active Trading Universe is EMPTY")
    else:
        logger.info(f"✅ Active Universe: {len(universe)} symbols ({universe[:5]}...)")

def main():
    app = create_app()
    with app.app_context():
        logger.info("=== STARTING SYSTEM HEALTH CHECK ===")
        r_ok = check_redis()
        d_ok = check_database()
        
        if r_ok:
            check_brain_status()
            
        if d_ok:
            check_active_models()
            
        check_trading_config()
        logger.info("=== CHECK COMPLETE ===")

if __name__ == "__main__":
    main()
