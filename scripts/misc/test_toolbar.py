#!/usr/bin/env python3
"""
Simple test server to check the RIBS toolbar visibility
"""
import os
from flask import Flask, render_template_string

app = Flask(__name__)

# Simple dashboard template with the RIBS toolbar
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .ribs-toolbar {
            border: 3px solid red;
            padding: 15px;
            margin: 20px 0;
            background: yellow;
            font-size: 18px;
            font-weight: bold;
        }
        .btn {
            background: #00d4aa;
            color: white;
            border: 2px solid #00b894;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 5px;
        }
        .btn-secondary { background: #6c757d; border-color: #5a6268; }
        .btn-primary { background: #007bff; border-color: #0056b3; }
    </style>
</head>
<body>
    <h1>Test Dashboard - RIBS Toolbar Visibility</h1>

    <div class="ribs-toolbar">
        <h3 style="margin: 0 0 10px 0; color: red;">🧬 RIBS EVOLUTION CONTROLS</h3>
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
            <button class="btn" onclick="alert('Refresh Logs clicked!')">
                🔄 REFRESH LOGS
            </button>
            <button class="btn btn-secondary" onclick="alert('View Logs clicked!')">
                📜 VIEW LOGS
            </button>
            <a href="#" class="btn btn-primary" onclick="alert('Go to RIBS Dashboard clicked!')">
                🧬 GO TO RIBS DASHBOARD
            </a>
        </div>
    </div>

    <p>If you can see a bright yellow box with red borders above containing the RIBS controls, then the toolbar is working!</p>
</body>
</html>
"""


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
