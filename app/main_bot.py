import os
import sys
import threading
import time
import logging
from werkzeug.serving import make_server

from app import create_app

# Initialize the Flask application
app = create_app()
from app.core.config_trading import TRADING_CONFIG
from app.runtime.symbols import get_active_trading_universe
from app.core.bot import (
    register_ai_bot_context,
    initialize_runtime_from_context,
    graceful_shutdown,
    shutdown_requested,
    historical_data,
    ultimate_trader,
    ultimate_ml_system,
    background_task_manager,
    TRADING_CONFIG as BOT_CONFIG # alias
)

def main():
    global shutdown_requested
    try:
        # Only initialize context if not already done (for direct execution)
        if not app.extensions.get("ai_bot_context"):
            ai_bot_context = register_ai_bot_context(app, force=True)
            # Initialize the ultimate system
            initialize_runtime_from_context(ai_bot_context)

        # Start the Flask web server
        host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
        port = int(os.environ.get("FLASK_RUN_PORT", 5000))
        print(f"🌐 Starting Flask web server on {host}:{port}...")

        # Create server
        server = make_server(host, port, app, threaded=True)

        # Start server in a separate thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()  # Remove daemon=True to keep server alive

        print(f"✅ Flask server started successfully on http://{host}:{port}")
        print(f"🎯 Dashboard available at: http://{host}:{port}")

        # Start all background tasks including self-improvement worker
        background_task_manager.start_background_tasks(
            start_ultimate_training=True,
            start_optimized_training=True,
            persistence_inputs={
                "trader": ultimate_trader,
                "ml_system": ultimate_ml_system,
                "config": TRADING_CONFIG,
                "symbols": list(get_active_trading_universe() or []),
                "historical_data": historical_data,
            },
        )

        # Start live portfolio scheduler
        background_task_manager.start_live_portfolio_updates()

        # Keep the main thread alive and handle server shutdown
        try:
            while server_thread.is_alive() and not shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Received keyboard interrupt - shutting down gracefully...")
            shutdown_requested = True

        # Shutdown server if it's still running
        if server_thread.is_alive():
            print("🛑 Shutting down Flask server...")
            server.shutdown()
            server_thread.join(timeout=5.0)

        graceful_shutdown()

    except Exception as e:
        print(f"\n❌ Fatal error during startup: {e}")
        graceful_shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()
