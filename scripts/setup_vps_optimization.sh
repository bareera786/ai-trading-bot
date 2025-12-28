#!/bin/bash
# VPS Optimization Script for AI Trading Bot
# Run this as root or with sudo

set -e

echo "========================================="
echo "AI Trading Bot VPS Optimization Setup"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: System Update${NC}"
apt-get update
apt-get upgrade -y

echo -e "${YELLOW}Step 2: Install Monitoring Tools${NC}"
apt-get install -y htop iotop glances nmon sysstat python3-pip python3-venv

echo -e "${YELLOW}Step 3: Configure Swap on NVMe${NC}"
# Create 8GB swap file on fast NVMe
SWAPFILE="/swapfile"
if [ ! -f "$SWAPFILE" ]; then
    fallocate -l 8G $SWAPFILE
    chmod 600 $SWAPFILE
    mkswap $SWAPFILE
    swapon $SWAPFILE
    echo "$SWAPFILE none swap sw 0 0" >> /etc/fstab
    echo -e "${GREEN}Swap file created${NC}"
else
    echo -e "${YELLOW}Swap file already exists${NC}"
fi

echo -e "${YELLOW}Step 4: Install and Configure ZRAM${NC}"
apt-get install -y zram-config
systemctl restart zram-config

echo -e "${YELLOW}Step 5: Kernel Optimizations for ML${NC}"
cat >> /etc/sysctl.conf << EOF

# AI Trading Bot Optimizations
# Memory Management
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1
vm.overcommit_ratio = 80

# Network for API calls
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000

# File System for NVMe
fs.file-max = 2097152
fs.nr_open = 2097152
EOF

sysctl -p

echo -e "${YELLOW}Step 6: Configure System Limits${NC}"
cat >> /etc/security/limits.conf << EOF
# AI Trading Bot Limits
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
EOF

echo -e "${YELLOW}Step 7: Create Trading Bot User${NC}"
if ! id "tradingbot" &>/dev/null; then
    useradd -m -s /bin/bash tradingbot
    echo -e "${GREEN}User tradingbot created${NC}"
else
    echo -e "${YELLOW}User tradingbot already exists${NC}"
fi

echo -e "${YELLOW}Step 8: Install Python Requirements${NC}"
sudo -u tradingbot bash << 'EOF'
cd /home/tradingbot
python3 -m venv bot_env
source bot_env/bin/activate
pip install --upgrade pip
pip install psutil pandas numpy scikit-learn xgboost lightgbm schedule joblib
EOF

echo -e "${YELLOW}Step 9: Create Monitoring Script${NC}"
cat > /usr/local/bin/monitor_bot.sh << 'EOF'
#!/bin/bash
echo "=== AI Trading Bot Monitor ==="
echo "Timestamp: $(date)"
echo ""
echo "=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2 " (" $3/$2*100 "%)"}')"
echo "Load Average: $(cat /proc/loadavg | awk '{print $1", "$2", "$3}')"
echo ""
echo "=== Disk Usage ==="
df -h / | tail -1
echo ""
echo "=== Process Info ==="
ps aux --sort=-%cpu | head -5 | awk '{print $2, $3, $4, $11}'
EOF

chmod +x /usr/local/bin/monitor_bot.sh

echo -e "${YELLOW}Step 10: Create Systemd Service${NC}"
cat > /etc/systemd/system/ai-trading-bot.service << EOF
[Unit]
Description=AI Trading Bot
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=tradingbot
Group=tradingbot
WorkingDirectory=/home/tradingbot/ai-trading-bot
Environment="PATH=/home/tradingbot/bot_env/bin"
ExecStart=/home/tradingbot/bot_env/bin/python /home/tradingbot/ai-trading-bot/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-trading-bot

# Resource limits
CPUQuota=80%
MemoryMax=12G
MemorySwapMax=4G
IOWeight=100
CPUSchedulingPolicy=rr
CPUSchedulingPriority=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. chmod +x /scripts/setup_vps_optimization.sh"
echo "2. sudo ./setup_vps_optimization.sh"
echo "3. systemctl start ai-trading-bot"
echo "4. systemctl enable ai-trading-bot"
echo "5. monitor with: journalctl -u ai-trading-bot -f"