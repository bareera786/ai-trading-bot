#!/bin/bash

# Find the project directory
PROJECT_DIR=$(find /home -name ai-trading-bot -type d 2>/dev/null | head -1)
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR=$(find / -name ai-trading-bot -type d 2>/dev/null | head -1)
fi

if [ -z "$PROJECT_DIR" ]; then
    echo "Project directory not found. Cloning repository..."
    cd ~
    git clone https://github.com/bareera786/ai-trading-bot.git
    PROJECT_DIR=~/ai-trading-bot
fi

cd "$PROJECT_DIR"

# Pull latest branch
git fetch origin
git checkout feature/timescaledb-integration
git pull origin feature/timescaledb-integration

# Restart TimescaleDB
docker compose -f docker-compose.timeseries.yml down
docker compose -f docker-compose.timeseries.yml up -d

# Wait for startup
sleep 10

# Check status
docker compose -f docker-compose.timeseries.yml ps

# Check logs
docker compose -f docker-compose.timeseries.yml logs --tail=20

# Verify extensions
docker compose -f docker-compose.timeseries.yml exec timescaledb psql -U timescale -d timescaledb -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"

# Verify tables
docker compose -f docker-compose.timeseries.yml exec timescaledb psql -U timescale -d timescaledb -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('ticks', 'candles', 'one_min_candles');"
