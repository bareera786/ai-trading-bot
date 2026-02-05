#!/usr/bin/env python3
"""
Inject Phase 6 Watchdog startup into wsgi.py
"""

import re

with open('wsgi.py', 'r') as f:
    content = f.read()

if 'ModelWatchdogService' in content:
    print("⚠️  Watchdog already present in wsgi.py")
    exit(0)

# We want to insert it after the background task manager logic
# Look for "bg_manager.start_live_portfolio_updates()"

target = 'bg_manager.start_live_portfolio_updates()'
injection = """bg_manager.start_live_portfolio_updates()
                
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
                    print(f"❌ WSGI: Failed to start Watchdog: {e}")"""

if target in content:
    new_content = content.replace(target, injection)
    with open('wsgi.py', 'w') as f:
        f.write(new_content)
    print("✅ Injected Watchdog startup into wsgi.py")
else:
    print("❌ Could not find injection point in wsgi.py")
    # Fallback: append to end if not found? No, unsafe.
