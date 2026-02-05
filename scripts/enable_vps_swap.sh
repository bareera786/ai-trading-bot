#!/bin/bash
# Script to add 4GB swap to VPS to prevent OOM kills
# Usage: ./scripts/enable_vps_swap.sh

VPS_HOST="151.243.171.80"
VPS_USER="aibot"
VPS_SSH_PORT="22"

echo "🔧 Setting up 4GB Swap on $VPS_USER@$VPS_HOST..."
echo "You may be asked for your SSH password multiple times."
echo ""

# Function to run remote command with interactive sudo
remote_sudo() {
    CMD="$1"
    ssh -t -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST "sudo bash -c '$CMD'"
}

remote_info() {
    CMD="$1"
    ssh -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST "$CMD"
}

# Check if swap already exists
echo "📊 Checking existing memory..."
remote_info "free -h"

echo ""
echo "⚙️  Creating 4GB Swapfile..."
# Create swapfile
remote_sudo "fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096"
remote_sudo "chmod 600 /swapfile"
remote_sudo "mkswap /swapfile"
remote_sudo "swapon /swapfile"

# Make permanent
echo "💾 Making swap permanent in /etc/fstab..."
remote_sudo "grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab"

# Tune swappiness (prefer RAM, use swap only when needed)
echo "🎛️  Tuning vm.swappiness to 10..."
remote_sudo "sysctl vm.swappiness=10"
remote_sudo "grep -q 'vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf"

echo ""
echo "✅ Swap setup complete. New memory stats:"
remote_info "free -h"
