#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

log() {
  printf '[mindstack-watchdog] %s\n' "$1"
}

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MASTER_ENV="$HOME/.config/docker/master-stack.env"
if [ -f "$MASTER_ENV" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$MASTER_ENV"
  set +a
fi

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  log "Warning: .venv not found; using system Python"
fi

VECTOR_CLI="${REPO_DIR}/src/codex_integration/vector_cli.py"
PYTHON_BIN="${PYTHON:-python3}"
if [ -x "$REPO_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$REPO_DIR/.venv/bin/python"
fi

INTERVAL="${MINDSTACK_WATCHDOG_INTERVAL:-60}"
RESTART_ON_FAILURE="${MINDSTACK_WATCHDOG_RESTART:-1}"
COMPOSE_FILE="${MINDSTACK_COMPOSE_FILE:-docker/docker-compose.yml}"
COMPOSE_SERVICES="${MINDSTACK_COMPOSE_SERVICES:-chroma qdrant meilisearch}"

check_mindstack() {
  "$PYTHON_BIN" "$VECTOR_CLI" status >/dev/null 2>&1
}

restart_services() {
  if [ "$RESTART_ON_FAILURE" -ne 1 ]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    log "docker command not found; cannot restart services"
    return 1
  fi
  log "Attempting to start Mindstack services via docker compose"
  docker compose -f "$COMPOSE_FILE" up -d $COMPOSE_SERVICES >/dev/null 2>&1 || \
    log "docker compose restart failed"
}

log "Watchdog started (interval=${INTERVAL}s, restart=${RESTART_ON_FAILURE})"

while true; do
  if check_mindstack; then
    sleep "$INTERVAL"
    continue
  fi

  log "Mindstack status check failed"
  restart_services || true
  sleep 10

done
