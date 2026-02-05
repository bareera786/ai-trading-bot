"""
Example: Integrating Dashboard Monitoring with Existing Flask Dashboard

This shows how to add the new monitoring capabilities to your existing Flask dashboard.
"""

from flask import Flask, jsonify, render_template_string
from main import AITradingBot
from integrations.dashboard_integration import integrate_with_existing_dashboard

# Initialize your bot (this will include dashboard monitoring)
bot = AITradingBot()

# Your existing Flask app
app = Flask(__name__)

# INTEGRATE NEW MONITORING - Add this single line!
integrate_with_existing_dashboard(app, bot.resource_manager)

# Your existing routes continue to work...
@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Trading Bot Dashboard</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    </head>
    <body>
        <h1>AI Trading Bot Dashboard</h1>

        <div id="metrics">
            <h2>System Metrics</h2>
            <div id="system-metrics">Loading...</div>

            <h2>Trading Performance</h2>
            <div id="trading-metrics">Loading...</div>
        </div>

        <script>
        function updateMetrics() {
            // Get system metrics
            $.get('/api/system-metrics', function(data) {
                $('#system-metrics').html(`
                    <p>CPU: ${data.metrics.cpu_percent.toFixed(1)}%</p>
                    <p>Memory: ${data.metrics.memory_percent.toFixed(1)}%</p>
                    <p>Health Score: ${data.health_score}/100</p>
                    <p>Bot Status: ${data.metrics.bot_status}</p>
                `);
            });

            // Update trading metrics (you can add this endpoint)
            $('#trading-metrics').html(`
                <p>Daily P&L: ${bot.daily_pnl || 0}%</p>
                <p>Active Pairs: ${bot.active_pairs.size || 0}</p>
                <p>Daily Trades: ${bot.daily_trade_count || 0}</p>
            `);
        }

        // Update every 5 seconds
        setInterval(updateMetrics, 5000);
        updateMetrics(); // Initial load
        </script>
    </body>
    </html>
    """)

@app.route('/api/trades')
def get_trades():
    # Your existing trade endpoint
    return jsonify({
        "trades": [],
        "daily_pnl": bot.daily_pnl,
        "active_pairs": list(bot.active_pairs),
        "total_trades": bot.daily_trade_count
    })

# NEW ENDPOINTS ARE AUTOMATICALLY ADDED:
# - GET /api/system-metrics
# - GET /api/resource-recommendations

if __name__ == '__main__':
    print("🚀 Enhanced Dashboard with AI Monitoring running!")
    print("📊 New endpoints available:")
    print("   - /api/system-metrics")
    print("   - /api/resource-recommendations")
    print("   - /api/trades (enhanced with bot metrics)")

    # Start bot in background thread
    import threading
    bot_thread = threading.Thread(target=lambda: bot.run(), daemon=True)
    bot_thread.start()

    app.run(debug=True, port=5000)