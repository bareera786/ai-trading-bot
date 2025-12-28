#!/bin/bash
# VPS Setup Script for AI Trading Bot (Docker stack)
# Run this on your VPS as root or with sudo

set -e

echo "🚀 Starting AI Trading Bot VPS Setup (Docker)..."
echo "==============================================="

if [[ $EUID -ne 0 ]]; then
     echo "❌ This script must be run as root or with sudo"
     exit 1
fi

APT_PKGS=(
    curl
    wget
    git
    htop
    ufw
    fail2ban
    ca-certificates
    gnupg
    lsb-release
)

echo "📦 Updating system packages..."
apt update && apt upgrade -y
echo "📦 Installing base utilities..."
apt install -y "${APT_PKGS[@]}"

echo "🐳 Installing Docker Engine and Compose plugin..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \\n+  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    tee /etc/apt/sources.list.d/docker.list >/dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "👤 Ensuring application user exists..."
useradd -m -s /bin/bash aibot 2>/dev/null || true
usermod -aG docker aibot

echo "📁 Preparing application directories..."
mkdir -p /home/aibot/ai-bot /home/aibot/backups
chown -R aibot:aibot /home/aibot

echo "🛡️  Configuring firewall (SSH + HTTP/HTTPS)..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force reload

echo "✅ Setup complete. Next steps:"
echo "1) Copy your repository to /home/aibot/ai-bot"
echo "2) As user 'aibot', run: docker compose -f docker-compose.prod.yml up -d --build"
echo "3) Verify: docker compose -f docker-compose.prod.yml ps"
echo "4) Logs: docker logs -f ai-trading-bot-prod"

echo "🎉 VPS ready for Docker deployment!"