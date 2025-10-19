#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

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
  echo "[launch-mcp-stack] Missing project virtual environment (.venv)." >&2
  echo "Run 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt' first." >&2
  exit 1
fi

profile="${MINDSTACK_PROFILE:-dev}"

if [ "$profile" = "production" ]; then
  export CODEX_VECTOR_BASE_URL="${CODEX_VECTOR_BASE_URL:-http://127.0.0.1:6333}"
  export CODEX_VECTOR_BACKEND="${CODEX_VECTOR_BACKEND:-qdrant}"
else
  export CODEX_VECTOR_BASE_URL="${CODEX_VECTOR_BASE_URL:-http://127.0.0.1:8000}"
  export CODEX_VECTOR_BACKEND="${CODEX_VECTOR_BACKEND:-chroma}"
fi

export CODEX_VECTOR_DIM="${CODEX_VECTOR_DIM:-384}"
export CODEX_EMBED_MODEL="${CODEX_EMBED_MODEL:-all-MiniLM-L6-v2}"
export CODEX_EMBED_PROVIDER="${CODEX_EMBED_PROVIDER:-auto}"

PYTHON_BIN="${PYTHON:-python3}"
if [ -x "$REPO_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$REPO_DIR/.venv/bin/python"
fi

VECTOR_CLI="$REPO_DIR/src/codex_integration/vector_cli.py"

ensure_mindstack_ready() {
  local retries="${MINDSTACK_READY_RETRIES:-10}"
  local delay="${MINDSTACK_READY_DELAY:-6}"
  local attempt=1
  echo "[launch-mcp-stack] Waiting for Mindstack to respond (retries=${retries}, delay=${delay}s)"
  while [ "$attempt" -le "$retries" ]; do
    if "$PYTHON_BIN" "$VECTOR_CLI" status >/dev/null 2>&1; then
      echo "[launch-mcp-stack] Mindstack is reachable"
      return 0
    fi
    echo "[launch-mcp-stack] Mindstack check failed (attempt $attempt). Retrying..."
    attempt=$((attempt + 1))
    sleep "$delay"
  done
  echo "[launch-mcp-stack] Warning: Mindstack did not respond after $((attempt - 1)) attempts" >&2
  return 1
}

if [ -z "${CODEX_MEILI_API_KEY:-}" ]; then
  echo "[launch-mcp-stack] CODEX_MEILI_API_KEY is required. Set a rotated Meilisearch master key." >&2
  exit 1
fi
if [[ "${CODEX_MEILI_API_KEY}" == dev-master-key-* || "${CODEX_MEILI_API_KEY}" == prod-master-key-* ]]; then
  echo "[launch-mcp-stack] Warning: CODEX_MEILI_API_KEY appears to use a placeholder value; rotate it via your secret manager." >&2
fi

run_sync=${RUN_VECTOR_SYNC:-1}
if [ "$run_sync" -eq 1 ]; then
  echo "[launch-mcp-stack] Refreshing vector collections via sync_documents.sh"
  scripts/codex/sync_documents.sh
fi

ensure_mindstack_ready || true

declare -a PIDS=()
trap 'echo "[launch-mcp-stack] Shutting down MCP servers"; for pid in "${PIDS[@]}"; do kill "$pid" >/dev/null 2>&1 || true; done' INT TERM

start_mcp() {
  local label=$1
  local process_name=$2
  shift 2
  if pgrep -f "$process_name" >/dev/null 2>&1; then
    echo "[launch-mcp-stack] $label already running; skipping"
    return 1
  fi
  echo "[launch-mcp-stack] Starting $label"
  "$@" &
  local pid=$!
  PIDS+=("$pid")
  return 0
}

start_helper() {
  local label=$1
  shift
  echo "[launch-mcp-stack] Starting $label"
  "$@" &
  local pid=$!
  PIDS+=("$pid")
}

start_docker=${START_DOCKER_MCP:-1}
start_github=${START_GITHUB_MCP:-1}
start_android_adb=${START_ANDROID_ADB_MCP:-1}
start_bitwarden=${START_BITWARDEN_MCP:-0}
start_google=${START_GOOGLE_MCP:-0}
start_watchdog=${START_MINDSTACK_WATCHDOG:-1}

if [ "$start_docker" -eq 1 ]; then
  start_mcp "Docker MCP" "mcp-server-docker" scripts/codex/run_docker_mcp.sh || true
else
  echo "[launch-mcp-stack] START_DOCKER_MCP=0 – skipping Docker MCP"
fi

if [ "$start_github" -eq 1 ]; then
  if [ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-${GITHUB_PAT:-}}" ]; then
    start_mcp "GitHub MCP" "github-mcp-server" scripts/codex/run_github_mcp.sh || true
  else
    echo "[launch-mcp-stack] Skipping GitHub MCP (no token set)"
  fi
else
  echo "[launch-mcp-stack] START_GITHUB_MCP=0 – skipping GitHub MCP"
fi

if [ "$start_android_adb" -eq 1 ]; then
  if command -v adb >/dev/null 2>&1; then
    start_mcp "Android ADB MCP" "android-adb-mcp-server" scripts/codex/run_android_adb_mcp.sh || true
  else
    echo "[launch-mcp-stack] Skipping Android ADB MCP (adb not found in PATH)"
  fi
else
  echo "[launch-mcp-stack] START_ANDROID_ADB_MCP=0 – skipping Android ADB MCP"
fi

if [ "$start_bitwarden" -eq 1 ]; then
  start_mcp "Bitwarden MCP" "bitwarden-mcp-server" scripts/codex/run_bitwarden_mcp.sh || true
else
  echo "[launch-mcp-stack] START_BITWARDEN_MCP=0 – skipping Bitwarden MCP"
fi

if [ "$start_google" -eq 1 ]; then
  start_mcp "Google Workspace MCP" "google_workspace_readonly" scripts/codex/run_google_mcp.sh || true
else
  echo "[launch-mcp-stack] START_GOOGLE_MCP=0 – skipping Google Workspace MCP"
fi

if [ "$start_watchdog" -eq 1 ]; then
  start_helper "Mindstack Watchdog" scripts/codex/mindstack_watchdog.sh
else
  echo "[launch-mcp-stack] START_MINDSTACK_WATCHDOG=0 – skipping Mindstack watchdog"
fi

if [ "${#PIDS[@]}" -eq 0 ]; then
  echo "[launch-mcp-stack] No background processes launched. Exiting."
  exit 0
fi

echo "[launch-mcp-stack] Services running. Press Ctrl+C to stop."
wait -n "${PIDS[@]}"
