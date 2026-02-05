
import sys
import os
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app import create_app
from app.bootstrap import bootstrap_runtime

from app.config import Config, DevelopmentConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManualTrain")

def train_manual():
    # Use DevelopmentConfig if available, else fallback to Config
    try:
        config_cls = DevelopmentConfig
    except NameError:
        config_cls = Config

    app = create_app(config_cls)
    
    with app.app_context():
        # Bootstrap to get the ML system
        logger.info("Bootstrapping runtime...")
        context = bootstrap_runtime(app)
        
        if not context:
            logger.error("Failed to bootstrap runtime context")
            return

        ultimate_ml_system = context.get("ultimate_ml_system")
        if not ultimate_ml_system:
            logger.error("Ultimate ML System not found in context")
            return

        logger.info("Starting training for BTCUSDT...")
        try:
            # Train on BTCUSDT using real data (or fallback checking)
            success = ultimate_ml_system.train_ultimate_model("BTCUSDT", use_real_data=True)
            if success:
                logger.info("✅ Training completed successfully for BTCUSDT")
            else:
                logger.error("❌ Training failed for BTCUSDT")
        except Exception as e:
            logger.exception(f"Training exception: {e}")

if __name__ == "__main__":
    train_manual()
