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
current_owner=$(stat -c "%u:%g" "$DATA_DIR" 2>/dev/null || echo "none")
if [ "$current_owner" != "${TARGET_UID}:${TARGET_GID}" ]; then
  echo "🔁 Adjusting ownership of $DATA_DIR -> ${TARGET_UID}:${TARGET_GID}"
  chown -R "${TARGET_UID}:${TARGET_GID}" "$DATA_DIR" 2>/dev/null || true
fi

# Ensure owner and group have read/write/execute where appropriate
chmod -R u+rwX,g+rwX "$DATA_DIR" 2>/dev/null || true

# Exec the container command
echo "▶ Running: $@"
exec "$@"
