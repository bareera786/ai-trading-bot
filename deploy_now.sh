#!/bin/bash
# Quick Deployment Helper
# Run this from the project root: /Users/tahir/Desktop/ai-bot

echo "🚀 AI Trading Bot - Quick Deploy"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "scripts/deployment/deploy_to_vps_complete.sh" ]; then
    echo "❌ ERROR: Must run from project root directory"
    echo ""
    echo "Run these commands:"
    echo "  cd /Users/tahir/Desktop/ai-bot"
    echo "  bash deploy_now.sh"
    exit 1
fi

# Check if config exists
if [ ! -f "config/deploy.env.production" ]; then
    echo "❌ ERROR: config/deploy.env.production not found"
    echo ""
    echo "Create it first with your VPS details"
    exit 1
fi

echo "✅ Running from correct directory"
echo "✅ Production config found"
echo ""
echo "🚀 Starting deployment..."
echo ""

# Run the deployment script
bash scripts/deployment/deploy_to_vps_complete.sh
