#!/bin/bash
# Complete persistence fix for AI Trading Bot

echo "🔧 Fixing AI Trading Bot Persistence Issues"
echo "=========================================="

# Kill running bot
echo "1. Stopping any running bot..."
pkill -f "start_server.py" 2>/dev/null
pkill -f "flask run" 2>/dev/null
sleep 2

# Find project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Docker usage
if [ -f "docker-compose.yml" ] || [ -f "docker-compose.prod.yml" ]; then
    echo "2. Docker setup detected..."
    echo "   Updating docker-compose files permissions..."
    
    for compose_file in docker-compose.yml docker-compose.prod.yml; do
        if [ -f "$compose_file" ]; then
            grep -q "user:" "$compose_file" || echo "    user: \"1000:1000\"" >> "$compose_file"
        fi
    done
    
    # Fix host directory permissions
    echo "3. Fixing host directory permissions for Docker..."
    sudo chown -R 1000:1000 ./bot_persistence 2>/dev/null || true
else
    echo "2. Local setup detected..."
fi

# Create directory structure
echo "4. Creating directory structure..."
mkdir -p bot_persistence/default/default/backups
mkdir -p bot_persistence/default/default/logs
mkdir -p bot_persistence/default/default/models

# Set permissions
echo "5. Setting permissions..."
chmod -R 755 bot_persistence 2>/dev/null || sudo chmod -R 755 bot_persistence
chmod -R 777 bot_persistence/default/default/backups 2>/dev/null || sudo chmod -R 777 bot_persistence/default/default/backups

# Create default state file
echo "6. Creating default state file..."
cat > bot_persistence/default/default/bot_state.json << EOF
{
  "state": "initialized",
  "trading_enabled": true,
  "paper_trading": true,
  "futures_trading_enabled": false,
  "last_updated": "$(date -Iseconds)",
  "version": "1.0.0",
  "profile": "default"
}
EOF

echo "7. Testing write access..."
touch bot_persistence/default/default/.test_write && rm bot_persistence/default/default/.test_write

if [ $? -eq 0 ]; then
    echo "✅ SUCCESS: Permissions fixed!"
    echo ""
    echo "🚀 Start your bot:"
    echo "   source .venv/bin/activate"
    echo "   python start_server.py"
else
    echo "❌ FAILED: Still have permission issues"
    echo ""
    echo "🔧 Alternative: Use temp directory"
    echo "   export BOT_PERSISTENCE_PATH=/tmp/bot_persistence"
    echo "   python start_server.py"
fi