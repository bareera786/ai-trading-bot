#!/bin/bash
set -e

# AI Trading Bot - VPS Deployment Script
# Tested on Ubuntu 20.04/22.04 LTS

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   AI Trading Bot - Production Deployment    ${NC}"
echo -e "${GREEN}=============================================${NC}"

# 1. System Update & Dependencies
echo -e "${YELLOW}[*] Updating system packages...${NC}"
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl apt-transport-https ca-certificates software-properties-common gnupg lsb-release

# 2. Install Docker & Docker Compose (if not present)
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[*] Installing Docker...${NC}"
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Enable Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo -e "${GREEN}[+] Docker installed successfully.${NC}"
else
    echo -e "${GREEN}[+] Docker is already installed.${NC}"
fi

# 3. Setup Configuration
echo -e "${YELLOW}[*] Setting up configuration...${NC}"
mkdir -p config bot_persistence logs credential

# Prompt for API Keys if .env doesn't exist
if [ ! -f config/deploy.env ]; then
    echo -e "${YELLOW}No configuration found. Starting setup wizard...${NC}"
    
    read -p "Enter Binance API Key: " BINANCE_KEY
    read -s -p "Enter Binance Secret Key: " BINANCE_SECRET
    echo ""
    read -p "Enter Database Password (default: secure_password_123): " DB_PASS
    DB_PASS=${DB_PASS:-secure_password_123}
    
    cat > config/deploy.env <<EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
BINANCE_API_KEY=${BINANCE_KEY}
BINANCE_API_SECRET=${BINANCE_SECRET}
POSTGRES_PASSWORD=${DB_PASS}
DATABASE_URL=postgresql://trading_user:${DB_PASS}@postgres:5432/trading_bot
REDIS_URL=redis://redis:6379/0
EOF
    echo -e "${GREEN}[+] Configuration saved to config/deploy.env${NC}"
else
    echo -e "${GREEN}[+] Using existing configuration in config/deploy.env${NC}"
fi

# 4. Build & Launch
echo -e "${YELLOW}[*] Building and starting containers...${NC}"

# Use the production compose file
# Ensure docker-compose.prod.yml uses Dockerfile.optimized
# We set user UID/GID to current user to avoid permission issues with volumes
export CONTAINER_UID=$(id -u)
export CONTAINER_GID=$(id -g)

docker compose -f docker-compose.prod.yml up -d --build

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   Deployment Complete! 🚀                   ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "Dashboard available at: http://<YOUR_VPS_IP>:5000"
echo -e "Check logs with: docker compose -f docker-compose.prod.yml logs -f"
echo -e "NOTE: You may need to logout and login again for Docker group permissions to take effect."
