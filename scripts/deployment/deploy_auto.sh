#!/bin/bash
# Complete VPS Deployment Script for AI Trading Bot (Automated with sshpass)

set -e

# Load configuration
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
    echo "✅ Using production configuration"
elif [ -f "config/deploy.env" ]; then
    source config/deploy.env
    echo "⚠️  Using legacy configuration"
else
    echo "❌ No config file found."
    exit 1
fi

VPS_HOST="${VPS_HOST:-your-vps-ip-or-domain}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

# Set the password provided by the user (injected via env var or hardcoded for this run)
VPS_PASS="${VPS_PASS:-tahir}"

echo "🚀 Starting AUTOMATED deployment to $VPS_USER@$VPS_HOST..."

# Check tools
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync required"; exit 1; }
command -v sshpass >/dev/null 2>&1 || { echo "❌ sshpass required"; exit 1; }

# Step 1: Sync files
echo "📦 Step 1: Syncing files..."
RSYNC_OPTS=(
    -rlt --inplace --no-perms --no-owner --no-group --no-times --progress
    --exclude ".DS_Store" --exclude ".coverage" --exclude ".pytest_cache/"
    --exclude ".git/" --exclude ".venv/" --exclude "__pycache__/"
    --exclude "*.pyc" --exclude "logs/" --exclude "bot_persistence/"
    --exclude "trade_data/" --exclude "optimized_trade_data/"
    --exclude "ultimate_models/" --exclude "optimized_models/"
    --exclude "futures_models/" --exclude "reports/"
    --exclude "config/deploy.env" --exclude "config/deploy.env.production"
    --exclude "*.pkl" --exclude "*.joblib" --exclude "htmlcov/"
    --exclude "node_modules/"
)

# Use sshpass for rsync
rsync "${RSYNC_OPTS[@]}" -e "sshpass -p '$VPS_PASS' ssh -p $VPS_SSH_PORT -o StrictHostKeyChecking=no" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced!"

# Step 2: Setup Remote
echo "🔧 Step 2: Configuring Remote..."

# Define SSH command with sshpass
SSH_CMD="sshpass -p '$VPS_PASS' ssh -p $VPS_SSH_PORT -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST"

# Create config dir
$SSH_CMD "mkdir -p $VPS_PATH/config"

# Write production env file (Careful with quoting!)
# We use a temporary local file then copy it to avoid complex escaping in the run command
cat > deploy.env.tmp <<EOF
DATABASE_URL=$DATABASE_URL
REDIS_URL=$REDIS_URL
FLASK_ENV=production
FLASK_APP=wsgi.py
SECRET_KEY=$SECRET_KEY
HOST=0.0.0.0
PORT=5000
LOG_LEVEL=INFO
LOG_FILE=/var/log/ai-trading-bot.log
RATE_LIMIT_STORAGE_URL=$REDIS_URL
VPS_HOST=$VPS_HOST
VPS_USER=$VPS_USER
VPS_PATH=$VPS_PATH
VPS_SSH_PORT=$VPS_SSH_PORT
CONTAINER_UID=1000
CONTAINER_GID=1000
EOF

# Copy the env file
rsync -e "sshpass -p '$VPS_PASS' ssh -p $VPS_SSH_PORT -o StrictHostKeyChecking=no" deploy.env.tmp "$VPS_USER@$VPS_HOST:$VPS_PATH/config/deploy.env.production"
rm deploy.env.tmp

echo "✅ Remote config updated"

# Step 3: Docker Deploy
echo "⚙️  Step 3: Deploying Docker..."
$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml build --pull ai-trading-bot"
$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml up -d ai-trading-bot"

echo "✅ Docker deployment completed!"
echo "🎉 Done."
