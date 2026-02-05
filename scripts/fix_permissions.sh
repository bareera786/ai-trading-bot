#!/bin/bash

# Fix Permissions Script
# Ensures correct ownership and permissions for the AI Trading Bot

echo "🔧 Starting Permission Fix..."

# Determine the user to own the files (default to current user)
TARGET_USER=${1:-$(whoami)}
TARGET_GROUP=${2:-$(id -gn)}

echo "👤 Target User: $TARGET_USER"
echo "👥 Target Group: $TARGET_GROUP"

# Project Root (current directory)
PROJECT_ROOT=$(pwd)

echo "📂 Project Root: $PROJECT_ROOT"

# 1. Ownership (Recursive)
echo "   -> Setting ownership..."
chown -R $TARGET_USER:$TARGET_GROUP "$PROJECT_ROOT"

# 2. Directory Permissions (755)
echo "   -> Setting directory permissions (755)..."
find "$PROJECT_ROOT" -type d -exec chmod 755 {} +

# 3. File Permissions (644)
echo "   -> Setting file permissions (644)..."
find "$PROJECT_ROOT" -type f -exec chmod 644 {} +

# 4. Executable Scripts (755)
echo "   -> Making scripts executable..."
find "$PROJECT_ROOT" -name "*.sh" -exec chmod +x {} +
find "$PROJECT_ROOT" -name "*.py" -exec chmod +x {} +
chmod +x "$PROJECT_ROOT/entrypoint.sh" 2>/dev/null || true

# 5. Secure Sensitive Files (600)
echo "   -> Securing sensitive files (600)..."
[ -f "$PROJECT_ROOT/.env" ] && chmod 600 "$PROJECT_ROOT/.env"
[ -f "$PROJECT_ROOT/config.py" ] && chmod 600 "$PROJECT_ROOT/config.py"

# 6. Ensure runtime directories are writable (777 to avoid UID mismatch issues in Docker)
echo "   -> Setting writable permissions for runtime directories..."
WRITABLE_DIRS=("logs" "bot_persistence" "reports" "credentials" "instance" "trade_data" "optimized_models")

for dir in "${WRITABLE_DIRS[@]}"; do
    mkdir -p "$PROJECT_ROOT/$dir"
    chmod -R 777 "$PROJECT_ROOT/$dir"
done

echo "✅ Permissions fixed successfully!"
