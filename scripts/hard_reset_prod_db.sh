#!/bin/bash
set -e

# Load config
source config/deploy.env

echo "☢️  HARD RESET: connecting to VPS ($VPS_HOST)..."
echo "⚠️  This will DESTROY the existing database volume and start fresh."

ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && \
    echo '🛑 Stopping all containers...' && \
    docker compose -f docker-compose.prod.yml down && \
    
    echo '🗑️  Removing database volume (postgres_data)...' && \
    docker volume rm ai-bot_postgres_data || true && \
    
    echo '🟢 Starting Postgres only...' && \
    docker compose -f docker-compose.prod.yml up -d postgres && \
    
    echo '⏳ Waiting for Postgres to initialize (15s)...' && \
    sleep 15 && \
    
    echo '🔄 Running Migrations (Lightweight - No ML Models)...' && \
    docker compose -f docker-compose.prod.yml run --rm --entrypoint \"flask db upgrade\" ai-trading-bot && \
    
    echo '👤 Creating Admin User...' && \
    docker compose -f docker-compose.prod.yml run --rm --entrypoint \"python create_admin_production.py\" ai-trading-bot && \
    
    echo '🚀 Starting Application...' && \
    docker compose -f docker-compose.prod.yml up -d"

echo "✅ Hard Reset Complete. You can now login with the admin credentials."
