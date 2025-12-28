#!/bin/bash
# Production Backup Script for AI Trading Bot
# Run this on your VPS as root or with sudo

set -e

BACKUP_DIR="/home/aibot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/home/aibot/ai-bot"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🚀 Starting production backup: $DATE"

# Database backup
echo "📊 Backing up PostgreSQL database..."
sudo -u postgres pg_dump ai_trading_bot > "$BACKUP_DIR/db_$DATE.sql"

# Application data backup (excluding logs and cache)
echo "📦 Backing up application data..."
tar -czf "$BACKUP_DIR/app_$DATE.tar.gz" \
    --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='logs/*' \
    --exclude='bot_persistence/backups/*' \
    --exclude='*.pyc' \
    "$APP_DIR/"

# Redis backup (if needed for persistence)
echo "💾 Backing up Redis data..."
redis-cli save
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb" 2>/dev/null || echo "Redis dump not available"

# Backup size information
DB_SIZE=$(du -h "$BACKUP_DIR/db_$DATE.sql" | cut -f1)
APP_SIZE=$(du -h "$BACKUP_DIR/app_$DATE.tar.gz" | cut -f1)
REDIS_SIZE=$(du -h "$BACKUP_DIR/redis_$DATE.rdb" 2>/dev/null | cut -f1 || echo "N/A")

echo "✅ Backup completed successfully!"
echo "📊 Database backup: $DB_SIZE ($BACKUP_DIR/db_$DATE.sql)"
echo "📦 Application backup: $APP_SIZE ($BACKUP_DIR/app_$DATE.tar.gz)"
echo "💾 Redis backup: $REDIS_SIZE ($BACKUP_DIR/redis_$DATE.rdb)"

# Clean old backups (keep last 7 days)
echo "🧹 Cleaning old backups..."
find "$BACKUP_DIR" -name "db_*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "app_*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +7 -delete

echo "✅ Backup cleanup completed!"
echo "📋 Total backups in $BACKUP_DIR:"
ls -la "$BACKUP_DIR"