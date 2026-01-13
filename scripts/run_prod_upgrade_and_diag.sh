#!/bin/bash
# One-shot script to run production upgrade and diagnostics on VPS
# Run this as: bash scripts/run_prod_upgrade_and_diag.sh
# It will prompt for admin password for smoke tests

set -e

echo "=== AI Bot Production Upgrade & Diagnostics ==="
echo "This script will:"
echo "1. Create DB backup"
echo "2. Pull latest branch"
echo "3. Rebuild app container"
echo "4. Run Alembic upgrade"
echo "5. Run diagnostics"
echo "6. Run smoke tests (login + toggle)"
echo "7. Save all logs to /tmp/ai-deploy-logs/"
echo ""

# Create log directory
mkdir -p /tmp/ai-deploy-logs

# 1. DB Backup
echo "1. Creating DB backup..."
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U trading_user trading_bot > /tmp/trading_bot_backup_$(date +%Y%m%d_%H%M%S).sql
echo "Backup created: $(ls -1 /tmp/trading_bot_backup_*.sql | tail -n1)" | tee /tmp/ai-deploy-logs/backup.log

# 2. Pull branch
echo "2. Pulling latest branch..."
git fetch origin
git checkout chore/idempotent-migrations || git checkout -b chore/idempotent-migrations origin/chore/idempotent-migrations
git reset --hard origin/chore/idempotent-migrations
echo "Branch updated." | tee /tmp/ai-deploy-logs/git.log

# 3. Rebuild app
echo "3. Rebuilding app container..."
docker compose -f docker-compose.prod.yml up -d --build ai-trading-bot
sleep 5
echo "App rebuilt and started." | tee /tmp/ai-deploy-logs/build.log

# 4. Alembic upgrade
echo "4. Running Alembic upgrade..."
docker compose -f docker-compose.prod.yml exec -T ai-trading-bot flask db upgrade 2>&1 | tee /tmp/ai-deploy-logs/alembic_upgrade.log
echo "Alembic exit code: $?" | tee -a /tmp/ai-deploy-logs/alembic_upgrade.log

# 5. Diagnostics
echo "5. Running diagnostics..."
docker compose -f docker-compose.prod.yml exec -T ai-trading-bot python scripts/diagnose_production.py 2>&1 | tee /tmp/ai-deploy-logs/diagnostics.log

# 6. Smoke tests
echo "6. Running smoke tests..."
read -p "Enter admin password for smoke tests: " ADMIN_PASS
echo "Testing login..."
curl -v -c /tmp/cookies.txt -H "Content-Type: application/json" -X POST -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASS\"}" http://127.0.0.1:5000/login 2>&1 | tee /tmp/ai-deploy-logs/login_test.log
echo "Testing toggle trading..."
curl -v -b /tmp/cookies.txt -X POST http://127.0.0.1:5000/api/toggle_trading 2>&1 | tee /tmp/ai-deploy-logs/toggle_test.log

# 7. Collect logs
echo "7. Collecting recent container logs..."
docker compose -f docker-compose.prod.yml logs --tail 400 ai-trading-bot > /tmp/ai-deploy-logs/container_logs.txt

echo ""
echo "=== Upgrade Complete ==="
echo "All logs saved to /tmp/ai-deploy-logs/"
echo "Key files:"
echo "  - Backup: $(ls -1 /tmp/trading_bot_backup_*.sql | tail -n1)"
echo "  - Alembic: /tmp/ai-deploy-logs/alembic_upgrade.log"
echo "  - Diagnostics: /tmp/ai-deploy-logs/diagnostics.log"
echo "  - Login test: /tmp/ai-deploy-logs/login_test.log"
echo "  - Toggle test: /tmp/ai-deploy-logs/toggle_test.log"
echo "  - Container logs: /tmp/ai-deploy-logs/container_logs.txt"
echo ""
echo "If any issues, check the logs and contact support."