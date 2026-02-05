#!/usr/bin/env bash
#
# Deployment helper for copying the AI bot to a VPS without Git.
# Usage:
#   VPS_HOST=example.com VPS_USER=aibot VPS_PATH=/home/aibot/ai-bot \
#   ./scripts/deploy_to_vps.sh
#
# Optional environment variables:
#   VPS_PORT        SSH port (default 22)
#   COMPOSE_FILE    Compose file path on VPS (default docker-compose.prod.yml)
#   DOCKER_SERVICE  Compose service name to (re)deploy (default ai-trading-bot)
#   SKIP_RESTART    Set to 1 to skip container restart
#   RSYNC_DELETE    Set to 1 to enable --delete during rsync
#   SYNC_MODELS     Set to 1 to include large trained model artifacts (*.pkl, *.joblib)
#   DEPLOY_ENV_FILE Path to a dotenv file with VPS_* values (default config/deploy.env)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEPLOY_ENV_FILE=${DEPLOY_ENV_FILE:-"${PROJECT_ROOT}/config/deploy.env"}
if [[ -f "${DEPLOY_ENV_FILE}" ]]; then
  printf "📄 Loading deployment env vars from %s\n" "${DEPLOY_ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${DEPLOY_ENV_FILE}"
  set +a
fi

: "${VPS_HOST:?VPS_HOST is required (e.g. vps.example.com)}"
: "${VPS_USER:?VPS_USER is required (e.g. aibot)}"
: "${VPS_PATH:?VPS_PATH is required (e.g. /home/aibot/ai-bot)}"

VPS_PORT=${VPS_PORT:-22}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
DOCKER_SERVICE=${DOCKER_SERVICE:-ai-trading-bot}
SKIP_RESTART=${SKIP_RESTART:-0}
RSYNC_DELETE=${RSYNC_DELETE:-0}
SYNC_STATE=${SYNC_STATE:-0}
SYNC_MODELS=${SYNC_MODELS:-0}

RSYNC_OPTS=("-az" "--progress" "--exclude" ".venv/" "--exclude" "__pycache__/" "--exclude" "*.pyc" "--exclude" "logs/" "--exclude" "bot_persistence/backups/")
if [[ "${RSYNC_DELETE}" == "1" ]]; then
  RSYNC_OPTS+=("--delete" "--delete-excluded")
fi
if [[ "${SYNC_STATE}" != "1" ]]; then
  RSYNC_OPTS+=("--exclude" "bot_persistence/" "--exclude" "trade_data/" "--exclude" "optimized_trade_data/")
fi
if [[ "${SYNC_MODELS}" != "1" ]]; then
  RSYNC_OPTS+=("--exclude" "*.pkl" "--exclude" "*.joblib" "--exclude" "models/" "--exclude" "model_cache/")
fi

REMOTE="${VPS_USER}@${VPS_HOST}"

printf "📦 Packaging project from %s\n" "${PROJECT_ROOT}"
rsync "${RSYNC_OPTS[@]}" -e "ssh -p ${VPS_PORT}" "${PROJECT_ROOT}/" "${REMOTE}:${VPS_PATH}/"

printf "✅ Files synced to %s:%s\n" "${REMOTE}" "${VPS_PATH}"

# Fix permissions if target owner is specified
VPS_TARGET_OWNER=${VPS_TARGET_OWNER:-"1001:1001"}
if [[ -n "${VPS_TARGET_OWNER}" ]]; then
  printf "🔧 Fixing permissions for %s...\n" "${VPS_TARGET_OWNER}"
  ssh -p "${VPS_PORT}" "${REMOTE}" "chown -R ${VPS_TARGET_OWNER} ${VPS_PATH}" || printf "⚠️  Could not change ownership (likely need root). Continuing...\n"
fi

REMOTE_COMMAND=$(cat <<EOF
cd "${VPS_PATH}" && \\
python3 -m compileall ai_ml_auto_bot_final.py
EOF
)

printf "⚙️  Running remote preflight checks...\n"
ssh -p "${VPS_PORT}" "${REMOTE}" "${REMOTE_COMMAND}"

if [[ "${SKIP_RESTART}" != "1" ]]; then
  printf "🔁 Rebuilding and restarting Docker service %s on %s...\n" "${DOCKER_SERVICE}" "${VPS_HOST}"
  ssh -tt -p "${VPS_PORT}" "${REMOTE}" "cd ${VPS_PATH} && docker compose -f ${COMPOSE_FILE} build --no-cache --pull ${DOCKER_SERVICE} && docker compose -f ${COMPOSE_FILE} up -d ${DOCKER_SERVICE}"

  printf "🗄️  Running surgical database schema fix...\n"
  # Run the python script to manually execute ALTER TABLE statements
  ssh -tt -p "${VPS_PORT}" "${REMOTE}" "cd ${VPS_PATH} && docker compose -f ${COMPOSE_FILE} exec -e FLASK_APP=ai_ml_auto_bot_final.py ${DOCKER_SERVICE} python scripts/fix_db_schema.py || echo '⚠️ Schema fix warning (check logs)'"

  printf "🔑 Ensuring Admin Access...\n"
  ssh -tt -p "${VPS_PORT}" "${REMOTE}" "cd ${VPS_PATH} && docker compose -f ${COMPOSE_FILE} exec -e FLASK_APP=ai_ml_auto_bot_final.py ${DOCKER_SERVICE} python scripts/ensure_admin_access.py"

  printf "🌐 Updating Host Nginx Configuration...\n"
  # Copy the host config to /etc/nginx/sites-available and reload
  # Check if site is enabled, if not link it
  ssh -tt -p "${VPS_PORT}" "${REMOTE}" "sudo cp ${VPS_PATH}/nginx/host_nginx.conf /etc/nginx/sites-available/ai-trading-bot && sudo ln -sf /etc/nginx/sites-available/ai-trading-bot /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx"

  printf "📜 Latest container logs (Ctrl+C to finish)...\n"
  ssh -tt -p "${VPS_PORT}" "${REMOTE}" "cd ${VPS_PATH} && docker compose -f ${COMPOSE_FILE} logs ${DOCKER_SERVICE} --tail 50"
else
  printf "⏭️  SKIP_RESTART=1 set; skipping service restart.\n"
fi

printf "🚀 Deployment completed.\n"
