#!/bin/bash
# Complete VPS Deployment Script for AI Trading Bot
# This script handles file transfer and Docker deployment

set -e  # Exit on any error

# Load configuration from production deploy.env
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
    echo "✅ Using production configuration from config/deploy.env.production"
elif [ -f "config/deploy.env" ]; then
    source config/deploy.env
    echo "⚠️  Using legacy configuration from config/deploy.env"
else
    echo "❌ No config/deploy.env.production or config/deploy.env found. Please create production config."
    exit 1
fi

# Set defaults if not specified
VPS_HOST="${VPS_HOST:-your-vps-ip-or-domain}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

echo "🚀 Starting complete AI Trading Bot deployment to VPS..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Check if required tools are installed
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync is required but not installed. Aborting."; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo "❌ ssh is required but not installed. Aborting."; exit 1; }

# Step 0: Pre-flight Permission Fix (Crucial for overwriting Docker files)
echo "🔧 Step 0: Fixing remote directory permissions..."
SSH_CMD="ssh -t -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"
# Ensure directory exists. Only use sudo if passwordless, otherwise skip (assume ownership ok)
$SSH_CMD "sudo -n mkdir -p $VPS_PATH 2>/dev/null || mkdir -p $VPS_PATH"
$SSH_CMD "sudo -n chown -R $VPS_USER: $VPS_PATH 2>/dev/null || echo '⚠️  Skipping sudo chown (password required or already owned)'"
echo "✅ Permission check done."
echo ""

# Step 1: Sync files to VPS
echo "📦 Step 1: Syncing files to VPS..."
RSYNC_OPTS=(
    -rlt
    -rlt
    --no-perms
    --no-owner
    --no-group
    --no-times
    --progress
    --exclude ".DS_Store"
    --exclude ".coverage"
    --exclude ".pytest_cache/"
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "*.pyc"
    --exclude "logs/"
    --exclude "bot_persistence/"  # never overwrite production state
    --exclude "bot_persistence_backup_new/" # Skip large backups
    --exclude "trade_data/"       # never overwrite production trade logs
    --exclude "optimized_trade_data/"
    --exclude "ultimate_models/"  # models can be large and are prod-owned
    --exclude "optimized_models/"
    --exclude "futures_models/" \
    --exclude "reports/"          # health reports generated on server
    --exclude "config/deploy.env" # never overwrite VPS secrets/config (unless fresh)
    --exclude "*.pkl"  # Skip large model files initially
    --exclude "*.joblib"
    --exclude "htmlcov/"  # Skip coverage reports
    --exclude "node_modules/"  # Skip if any
)

rsync "${RSYNC_OPTS[@]}" -e "ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced successfully!"
echo ""

# Step 2: Setup production environment on VPS
echo "🔧 Step 2: Setting up production environment on VPS..."

SSH_CMD="ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

# Setup production config on VPS
echo "📝 Setting up production configuration on VPS..."
$SSH_CMD "mkdir -p $VPS_PATH/config"

# We now upload the file directly via rsync, so just ensure it exists and copy to deploy.env for docker-compose
$SSH_CMD "if [ -f $VPS_PATH/config/deploy.env.production ]; then \
    cp $VPS_PATH/config/deploy.env.production $VPS_PATH/config/deploy.env; \
    echo '✅ Config synced to deploy.env'; \
else \
    echo '❌ Missing config/deploy.env.production on remote!'; exit 1; \
fi"

# Secure the env file and set ownership
echo "🔒 Securing remote env file"
$SSH_CMD "chmod 600 $VPS_PATH/config/deploy.env.production $VPS_PATH/config/deploy.env || true"
# Non-interactive sudo or user-level ownership
$SSH_CMD "sudo -n chown $VPS_USER: $VPS_PATH/config/deploy.env.production $VPS_PATH/config/deploy.env 2>/dev/null || true"

echo "✅ Production config secured on VPS"

# Ensure persistence directory ownership is correct (run inside a short-lived container)
# Basic remote pre-checks
echo "🔎 Checking remote host prerequisites (docker, user)"
$SSH_CMD "if ! command -v docker >/dev/null 2>&1; then echo 'WARNING: docker not found on VPS'; fi"
# Only try useradd if we have root access
$SSH_CMD "id -u $VPS_USER >/dev/null 2>&1 || (sudo -n useradd -m -s /bin/bash $VPS_USER 2>/dev/null || echo 'WARNING: Could not create user $VPS_USER; ensure it exists')"

echo "🔧 Adjusting ownership of persistence dir on VPS (if needed)"
# Best-effort chown
$SSH_CMD "sudo -n chown -R $VPS_USER: $VPS_PATH 2>/dev/null" || true

# Optionally install Docker (Only if passwordless sudo available)
if [ "${INSTALL_DOCKER_ON_VPS:-0}" = "1" ]; then
    if $SSH_CMD "sudo -n true 2>/dev/null"; then
        echo "⬇️  INSTALL_DOCKER_ON_VPS=1 set — installing Docker & Compose on remote host"
        $SSH_CMD "set -euo pipefail; \
            sudo -n apt-get update -y || true; \
            sudo -n apt-get install -y ca-certificates curl gnupg lsb-release software-properties-common || true; \
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo -n gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg || true; \
            echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo -n tee /etc/apt/sources.list.d/docker.list > /dev/null; \
            sudo -n apt-get update -y || true; \
            sudo -n apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || true; \
            sudo -n usermod -aG docker $VPS_USER || true;"
        echo "✅ Remote Docker installation step finished"
    else
        echo "⚠️  Skipping Docker Install (sudo password required)"
    fi
fi

# Ensure reports directory exists
echo "🔧 Ensuring default health report exists on VPS"
$SSH_CMD "mkdir -p $VPS_PATH/reports && if [ ! -f $VPS_PATH/reports/backtest_top10.json ]; then echo '{\"generated_at\": null, \"aggregate_summary\": {}, \"symbol_summaries\": {}}' > $VPS_PATH/reports/backtest_top10.json; fi"
# Try permission fix if possible
$SSH_CMD "sudo -n chown -R $VPS_USER: $VPS_PATH/reports 2>/dev/null && sudo -n chmod -R u+rwX,g+rwX $VPS_PATH/reports 2>/dev/null" || true
echo ""

# Pre-deployment: Stop conflicting services on Port 80
echo "🔌 Checking for port 80 conflicts on VPS..."
$SSH_CMD "if sudo -n lsof -i :80 >/dev/null 2>&1; then 
    echo '⚠️  Port 80 is in use. Attempting to stop conflicting services...';
    sudo -n systemctl stop apache2 2>/dev/null || true;
    sudo -n systemctl disable apache2 2>/dev/null || true;
    sudo -n systemctl stop nginx 2>/dev/null || true;
    sudo -n systemctl disable nginx 2>/dev/null || true;
    echo '✅ Freed port 80.';
else
    echo '✅ Port 80 check skipped (free or no sudo)';
fi"

# Step 2.5: Cleanup Docker to free space
echo "🧹 Step 2.5: Cleaning up unused Docker images..."
$SSH_CMD "docker system prune -af" || true
echo "✅ Docker cleanup complete"
echo ""

# Step 3: Deploy Docker service on VPS
echo "⚙️  Step 3: Deploying Docker Compose on VPS..."

SSH_CMD="ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml build --pull"
$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml up -d"


echo "✅ Docker deployment completed"
echo ""

# Force restart to ensure entrypoint runs freshly
echo "🔄 Forcing container restart to apply DB migrations..."
$SSH_CMD "cd $VPS_PATH && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d"

echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Your bot should be accessible at: http://$VPS_HOST:5000"
echo "📊 Prometheus metrics at: http://$VPS_HOST:9090/metrics"
echo ""
echo "📋 Useful commands on your VPS:"
echo "  Status: docker compose -f docker-compose.prod.yml ps ai-trading-bot"
echo "  Logs:   docker logs -f ai-trading-bot-prod"
echo "  Redeploy: cd $VPS_PATH && docker compose -f docker-compose.prod.yml up -d --build ai-trading-bot"
echo "  Metrics: curl http://localhost:9090/metrics"
echo ""
echo "🔧 To update the bot later, run this script again to sync and rebuild."
