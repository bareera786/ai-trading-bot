#!/bin/bash
# VPS Setup Script for AI Trading Bot Production Deployment
# Run this on your VPS as root or with sudo

set -e

echo "🚀 Starting AI Trading Bot VPS Setup..."
echo "========================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root or with sudo"
   exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
echo "📦 Installing essential packages..."
apt install -y \
    curl \
    wget \
    git \
    htop \
    iotop \
    sysstat \
    ufw \
    fail2ban \
    unattended-upgrades \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Python 3.9+
echo "🐍 Installing Python 3.9+..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.9 python3.9-venv python3-pip python3.9-dev

# Install PostgreSQL
echo "🐘 Installing PostgreSQL..."
apt install -y postgresql postgresql-contrib

# Install Redis
echo "💾 Installing Redis..."
apt install -y redis-server

# Install Nginx
echo "🌐 Installing Nginx..."
apt install -y nginx

# Install Certbot for SSL
echo "🔒 Installing Certbot for SSL certificates..."
apt install -y certbot python3-certbot-nginx

# Configure PostgreSQL
echo "⚙️  Configuring PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE ai_trading_bot;
CREATE USER aibot WITH PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE ai_trading_bot TO aibot;
ALTER USER aibot CREATEDB;
EOF

echo "✅ Database 'ai_trading_bot' created with user 'aibot'"

# Configure Redis
echo "⚙️  Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Configure Nginx
echo "⚙️  Configuring Nginx..."
systemctl enable nginx
systemctl start nginx

# Configure firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force reload

# Configure automatic security updates
echo "🔒 Configuring automatic security updates..."
dpkg-reconfigure --priority=low unattended-upgrades

# Create application user
echo "👤 Creating application user..."
useradd -m -s /bin/bash aibot || echo "User aibot already exists"

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p /home/aibot/ai-bot
mkdir -p /home/aibot/backups
mkdir -p /home/aibot/ai-bot/logs
chown -R aibot:aibot /home/aibot

# Install Node.js for asset building (if needed)
echo "📦 Installing Node.js for asset building..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Install PM2 for process management (optional)
echo "📦 Installing PM2 for process management..."
npm install -g pm2

# Configure log rotation
echo "📝 Configuring log rotation..."
cat > /etc/logrotate.d/ai-trading-bot << EOF
/home/aibot/ai-bot/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 aibot aibot
    postrotate
        systemctl reload ai-trading-bot
    endscript
}
EOF

# Set up cron jobs for backups
echo "⏰ Setting up automated backups..."
echo "0 2 * * * /home/aibot/ai-bot/scripts/backup_production.sh" | crontab -u aibot -

# Configure fail2ban
echo "🛡️  Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

echo ""
echo "🎉 VPS setup completed successfully!"
echo "===================================="
echo ""
echo "📋 Next steps:"
echo "1. Update the database password in PostgreSQL:"
echo "   sudo -u postgres psql -c \"ALTER USER aibot PASSWORD 'your_secure_password';\""
echo ""
echo "2. Copy your application code to /home/aibot/ai-bot/"
echo ""
echo "3. Set up SSL certificate:"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "4. Update Nginx configuration:"
echo "   sudo cp /home/aibot/ai-bot/nginx.conf /etc/nginx/sites-available/ai-trading-bot"
echo "   sudo ln -s /etc/nginx/sites-available/ai-trading-bot /etc/nginx/sites-enabled/"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "5. Deploy your application:"
echo "   sudo cp /home/aibot/ai-bot/ai-trading-bot.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable ai-trading-bot"
echo "   sudo systemctl start ai-trading-bot"
echo ""
echo "6. Verify installation:"
echo "   sudo systemctl status ai-trading-bot"
echo "   curl http://localhost:8000/health"
echo ""
echo "🔧 Useful commands:"
echo "  Service management: sudo systemctl [start|stop|restart|status] ai-trading-bot"
echo "  View logs: sudo journalctl -u ai-trading-bot -f"
echo "  Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "  Database access: sudo -u postgres psql -d ai_trading_bot"