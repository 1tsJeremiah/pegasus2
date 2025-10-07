#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Source optional env file if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN:-${GITHUB_PAT:-}}"
if [ -z "${TOKEN}" ]; then
  echo "[github-mcp] Please export GITHUB_PAT or GITHUB_PERSONAL_ACCESS_TOKEN before running." >&2
  exit 1
fi

export GITHUB_PERSONAL_ACCESS_TOKEN="$TOKEN"

if ! command -v github-mcp-server >/dev/null 2>&1; then
  echo "[github-mcp] github-mcp-server binary not found in PATH" >&2
  exit 1
fi

exec github-mcp-server stdio --toolsets=context,repos,issues,pull_requests,actions
