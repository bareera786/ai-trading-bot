#!/bin/bash
# Phase 6 Integration Script
# This script applies all pending integrations automatically

set -e

echo "🚀 Applying Phase 6 integrations..."

# 1. Add route registration to brain.py
echo "📝 Step 1: Registering Phase 6 routes..."
sed -i.bak '/brain_bp = Blueprint/a\
\
# Phase 6: Register performance governance routes\
from app.routes.brain_phase6 import register_phase6_routes\
register_phase6_routes(brain_bp)
' app/routes/brain.py

echo "✅ Routes registered"

# 2. Add watchdog thread to start_server.py
echo "📝 Step 2: Adding watchdog thread initialization..."

cat >> start_server.py << 'EOF'

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

EOF

echo "✅ Watchdog thread added"

echo ""
echo "🎉 Phase 6 backend integrations complete!"
echo ""
echo "Next: Add UI components to brain_dashboard.html"
echo "Run: python scripts/add_phase6_ui.py"
