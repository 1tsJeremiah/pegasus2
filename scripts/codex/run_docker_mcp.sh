#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export DOCKER_HOST="unix:///var/run/docker.sock"

if ! command -v mcp-server-docker >/dev/null 2>&1; then
  echo "[run-docker-mcp] mcp-server-docker is not available in PATH" >&2
  exit 1
fi

exec mcp-server-docker
