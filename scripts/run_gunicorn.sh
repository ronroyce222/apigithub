#!/bin/bash
# Start the FastAPI application with Gunicorn and SSL.
#
# Usage:
#   ./scripts/run_gunicorn.sh
#
# Environment variables (with defaults):
#   HOST            - Bind address        (default: 0.0.0.0)
#   PORT            - Bind port           (default: 8080)
#   WORKERS         - Worker count        (default: CPU cores * 2 + 1)
#   SSL_CERTFILE    - SSL certificate     (default: certs/fullchain.pem)
#   SSL_KEYFILE     - SSL private key     (default: certs/privkey.pem)
#   LOG_LEVEL       - Gunicorn log level  (default: info)
#   TIMEOUT         - Worker timeout secs (default: 120)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $1"
}

die() {
    log "ERROR: $1"
    exit 1
}

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-$(python3 -c \
    'import os; print(os.cpu_count() * 2 + 1)')}"
LOG_LEVEL="${LOG_LEVEL:-info}"
TIMEOUT="${TIMEOUT:-120}"

SSL_CERTFILE="${SSL_CERTFILE:-${PROJECT_DIR}/certs/fullchain.pem}"
SSL_KEYFILE="${SSL_KEYFILE:-${PROJECT_DIR}/certs/privkey.pem}"

# --- Validate SSL certificates ---
[ -f "$SSL_CERTFILE" ] || die "SSL cert not found: ${SSL_CERTFILE}"
[ -f "$SSL_KEYFILE" ]  || die "SSL key not found: ${SSL_KEYFILE}"

log "INFO: Starting Gunicorn with SSL"
log "INFO: bind=${HOST}:${PORT} workers=${WORKERS}"
log "INFO: certfile=${SSL_CERTFILE}"
log "INFO: keyfile=${SSL_KEYFILE}"

cd "$PROJECT_DIR/src"

exec gunicorn main:app \
    --bind "${HOST}:${PORT}" \
    --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --certfile "$SSL_CERTFILE" \
    --keyfile "$SSL_KEYFILE" \
    --timeout "$TIMEOUT" \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level "$LOG_LEVEL"
