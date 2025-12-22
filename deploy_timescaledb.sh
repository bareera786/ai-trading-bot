#!/bin/bash

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
