#!/bin/bash
# Quick VPS Deployment Script for AI Trading Bot with Optimizations
# Usage: ./quick_deploy_optimized.sh your-vps.com your-user

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <vps-host> <vps-user> [vps-path]"
    echo "Example: $0 vps.example.com aibot /home/aibot/ai-bot"
    exit 1
fi

VPS_HOST=$1
VPS_USER=$2
VPS_PATH=${3:-"/home/$VPS_USER/ai-bot"}

echo "🚀 Quick Deployment to $VPS_HOST"
echo "================================="

# Check if deploy.env exists
if [ ! -f "config/deploy.env" ]; then
    echo "📝 Creating deployment config..."
    cp config/deploy.env.example config/deploy.env
    echo "⚠️  Please edit config/deploy.env with your VPS settings"
    echo "   Then run this script again"
    exit 1
fi

echo "📤 Copying optimization setup script..."
scp scripts/setup_vps_optimization.sh $VPS_USER@$VPS_HOST:/tmp/

echo "🔧 Running VPS optimization..."
ssh $VPS_USER@$VPS_HOST "sudo bash /tmp/setup_vps_optimization.sh"

echo "🚀 Deploying optimized bot..."
VPS_HOST=$VPS_HOST VPS_USER=$VPS_USER VPS_PATH=$VPS_PATH ./scripts/deploy_to_vps.sh

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🌐 Access your dashboard at: http://$VPS_HOST"
echo "📊 Monitor system health and alerts in real-time"
echo ""
echo "📚 Integration Options:"
echo "1. Quick Integration (recommended): Add to your main bot file:"
echo "   from quick_integration import add_optimization_to_existing_bot"
echo "   optimization = add_optimization_to_existing_bot()"
echo ""
echo "2. Minimal Changes: Add to training/trading functions:"
echo "   from simple_optimize import should_train_now, limit_training_resources"
echo ""
echo "🎯 Your AI trading bot is now optimized for production!"