
# ============================================================================
# PHASE 6: MODEL WATCHDOG THREAD
# ============================================================================

def start_watchdog_thread():
    """Start background watchdog monitoring thread."""
    import threading
    import time
    from app.services.model_watchdog_service import ModelWatchdogService
    
    def watchdog_loop():
        logger.info("🐕 Model Watchdog started")
        while True:
            try:
                with app.app_context():
                    ModelWatchdogService.run_watchdog_cycle()
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
            
            time.sleep(60)  # Run every 60 seconds
    
    thread = threading.Thread(target=watchdog_loop, daemon=True)
    thread.start()
    logger.info("✅ Watchdog thread started")

# Start watchdog on application boot
import os
if not os.getenv('SKIP_RUNTIME_BOOTSTRAP'):
    start_watchdog_thread()

