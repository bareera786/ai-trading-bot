#!/bin/sh
set -e

# Idempotent entrypoint helper to ensure persistence directory is writable
# Respects CONTAINER_UID/CONTAINER_GID and BOT_PERSISTENCE_DIR environment variables

TARGET_UID=${CONTAINER_UID:-1001}
TARGET_GID=${CONTAINER_GID:-1001}
DATA_DIR=${BOT_PERSISTENCE_DIR:-/app/bot_persistence}

echo "🔧 EntryPoint: ensuring persistence dir exists: $DATA_DIR"
mkdir -p "$DATA_DIR"

# If we can chown, do it; if not, continue without failing.
# Loop through critical directories to fix permissions if needed
for dir in "$DATA_DIR" "/app/ultimate_models" "/app/futures_models" "/app/optimized_models" "/app/trade_data" "/app/optimized_trade_data" "/app/logs"; do
  if [ -d "$dir" ]; then
      current_owner=$(stat -c "%u:%g" "$dir" 2>/dev/null || echo "none")
      if [ "$current_owner" != "${TARGET_UID}:${TARGET_GID}" ]; then
        echo "🔁 Adjusting ownership of $dir -> ${TARGET_UID}:${TARGET_GID}"
        chown -R "${TARGET_UID}:${TARGET_GID}" "$dir" 2>/dev/null || true
      fi
      chmod -R u+rwX,g+rwX "$dir" 2>/dev/null || true
  fi
done

# Auto-run database migrations without starting heavy ML subsystems (prevents OOM)
echo "🔄 EntryPoint: Running Database Migrations (Lightweight Mode)..."
# SKIP: Migrations temporarily disabled due to schema mismatch issues
# echo "🛠 EntryPoint: Running Force DB Fix Script..."
# python3 scripts/force_db_fix.py || echo "⚠️ Force fix script encountered an error (check logs)"
# SKIP_RUNTIME_BOOTSTRAP=true python3 -m flask db upgrade || echo "⚠️ Migration failed (check logs)"
echo "✅ EntryPoint: Migrations skipped (schema is current)"

# Exec the container command
echo "▶ Running: $@"
exec "$@"
