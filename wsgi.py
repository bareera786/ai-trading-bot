#!/usr/bin/env python3
"""
WSGI application for the AI Trading Bot
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set production environment
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app

application = create_app()

# ==================== PRODUCTION SERVICE STARTUP ====================
# In production (Gunicorn), we must explicitly start background services
# because the Flask reloader's main block is not executed.
try:
    print("🚀 WSGI: Initializing background services for production...")
    
    # Allow time for extensions to initialize
    with application.app_context():
        ctx = application.extensions.get("ai_bot_context")
        if ctx:
            bg_manager = ctx.get("background_task_manager")
            if bg_manager:
                # Retrieve dependencies from context
                ultimate_trader = ctx.get("ultimate_trader")
                ultimate_ml_system = ctx.get("ultimate_ml_system")
                trading_config = ctx.get("trading_config", {})
                historical_data = ctx.get("historical_data")
                
                # Get active symbols (try multiple sources)
                from app.runtime.symbols import get_active_trading_universe
                active_symbols = list(get_active_trading_universe() or [])

                print(f"   - Starting services with {len(active_symbols)} symbols")
                
                bg_manager.start_background_tasks(
                    start_ultimate_training=True,
                    start_optimized_training=True,
                    persistence_inputs={
                        "trader": ultimate_trader,
                        "ml_system": ultimate_ml_system,
                        "config": trading_config,
                        "symbols": active_symbols,
                        "historical_data": historical_data,
                    },
                )
                
                # Ensure live portfolio updates are running
                bg_manager.start_live_portfolio_updates()
                
                # ==================== PHASE 6: MODEL WATCHDOG ====================
                print("🐕 WSGI: Starting Model Watchdog...")
                try:
                    from app.services.model_watchdog_service import ModelWatchdogService
                    import threading
                    import time
                    
                    def watchdog_loop():
                        print("🐕 Model Watchdog thread active")
                        while True:
                            try:
                                # Use the global application object for context
                                with application.app_context():
                                    ModelWatchdogService.run_watchdog_cycle()
                            except Exception as e:
                                print(f"❌ Watchdog error: {e}")
                            
                            time.sleep(60)  # Run every 60 seconds
                    
                    wd_thread = threading.Thread(target=watchdog_loop, daemon=True)
                    wd_thread.start()
                    print("✅ WSGI: Model Watchdog started")
                except Exception as e:
                    print(f"❌ WSGI: Failed to start Watchdog: {e}")
                
                print("✅ WSGI: Background services started successfully")
            else:
                print("⚠️ WSGI: Background task manager not found in context")
        else:
            print("⚠️ WSGI: AI bot context not found in application extensions")

except Exception as e:
    print(f"❌ WSGI: Failed to start background services: {e}")
    # Don't crash the server, just log the error
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=False, threaded=False)
