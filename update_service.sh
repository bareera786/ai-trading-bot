#!/bin/bash
# Update systemd service file to use gunicorn
echo "🔧 Updating systemd service file to use gunicorn..."

# Backup current service file
sudo cp /etc/systemd/system/ai-trading-bot.service /etc/systemd/system/ai-trading-bot.service.backup

# Create new service file with gunicorn
sudo tee /etc/systemd/system/ai-trading-bot.service > /dev/null << 'EOF'
[Unit]
Description=AI Trading Bot Flask Application
After=network.target

[Service]
User=aibot
WorkingDirectory=/home/aibot/ai-bot
Environment="BOT_LOG_DIR=/home/aibot/ai-bot/logs"
Environment="BOT_LOG_LEVEL=INFO"
Environment="FLASK_RUN_PORT=5000"
Environment="FLASK_ENV=production"
ExecStart=/home/aibot/ai-bot/.venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --timeout 120 wsgi:application
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file updated!"
echo "Reloading systemd and restarting service..."

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart ai-trading-bot.service

# Check status
echo "Service status:"
sudo systemctl status ai-trading-bot.service