"""
Example: How to integrate dashboard monitoring with existing Flask dashboard

This shows how to add the new monitoring capabilities to your existing dashboard.
"""

from flask import Flask, jsonify
from config.resource_manager import ResourceManager
from integrations.dashboard_integration import integrate_with_existing_dashboard

# Your existing Flask app
app = Flask(__name__)

# Initialize resource manager (assuming you have one)
resource_manager = ResourceManager()

# INTEGRATE NEW MONITORING - Add this line to your existing dashboard
integrate_with_existing_dashboard(app, resource_manager)

# Your existing routes continue to work...
@app.route('/')
def dashboard():
    return "Your existing dashboard"

@app.route('/api/trades')
def get_trades():
    # Your existing trade endpoint
    return jsonify({"trades": []})

# NEW ENDPOINTS ARE AUTOMATICALLY ADDED:
# - GET /api/system-metrics
# - GET /api/resource-recommendations
# - WebSocket support for real-time updates (if using SocketIO)

if __name__ == '__main__':
    print("🚀 Dashboard with enhanced monitoring running!")
    print("📊 New endpoints available:")
    print("   - /api/system-metrics")
    print("   - /api/resource-recommendations")
    app.run(debug=True, port=5000)