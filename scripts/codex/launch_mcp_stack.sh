#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "[launch-mcp-stack] Missing project virtual environment (.venv)." >&2
  echo "Run 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt' first." >&2
  exit 1
fi

export CODEX_VECTOR_BASE_URL="${CODEX_VECTOR_BASE_URL:-http://127.0.0.1:8000/api/v2}"
export CODEX_VECTOR_DIM="${CODEX_VECTOR_DIM:-384}"
export CODEX_EMBED_PROVIDER="${CODEX_EMBED_PROVIDER:-hash}"

run_sync=${RUN_VECTOR_SYNC:-1}
if [ "$run_sync" -eq 1 ]; then
  echo "[launch-mcp-stack] Refreshing vector collections via sync_documents.sh"
  scripts/codex/sync_documents.sh
fi

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

start_docker=${START_DOCKER_MCP:-1}
start_github=${START_GITHUB_MCP:-1}

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

if [ "${#PIDS[@]}" -eq 0 ]; then
  echo "[launch-mcp-stack] No MCP servers launched. Exiting."
  exit 0
fi

echo "[launch-mcp-stack] MCP servers running. Press Ctrl+C to stop."
wait -n "${PIDS[@]}"
