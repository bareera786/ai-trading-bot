#!/bin/bash
# Fix database permissions for AI Trading Bot
# Run this on your VPS as root or with sudo

echo "🔧 Fixing database permissions for AI Trading Bot..."

# Database file location
DB_FILE="/home/aibot/ai-bot/trading_bot.db"
INSTANCE_DB="/home/aibot/ai-bot/instance/trading_bot.db"

# Check if running as root or sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root or with sudo"
   exit 1
fi

# Fix permissions for database files
if [ -f "$DB_FILE" ]; then
    echo "📁 Fixing permissions for $DB_FILE"
    chown aibot:aibot "$DB_FILE"
    chmod 664 "$DB_FILE"
    echo "✅ Fixed permissions for $DB_FILE"
fi

if [ -f "$INSTANCE_DB" ]; then
    echo "📁 Fixing permissions for $INSTANCE_DB"
    chown aibot:aibot "$INSTANCE_DB"
    chmod 664 "$INSTANCE_DB"
    echo "✅ Fixed permissions for $INSTANCE_DB"
fi

# Also fix permissions for the instance directory
if [ -d "/home/aibot/ai-bot/instance" ]; then
    echo "📁 Fixing permissions for instance directory"
    chown -R aibot:aibot "/home/aibot/ai-bot/instance"
    chmod -R 755 "/home/aibot/ai-bot/instance"
    echo "✅ Fixed permissions for instance directory"
fi

# Restart the service to pick up changes
echo "🔄 Restarting AI Trading Bot service..."
systemctl restart ai-trading-bot

# Check service status
echo "📊 Service status:"
systemctl status ai-trading-bot --no-pager

echo ""
echo "🎉 Database permissions fixed!"
echo "✅ User management operations should now work correctly."