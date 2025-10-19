#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BITWARDEN_DIR="${BITWARDEN_MCP_PATH:-$HOME/bitwarden-mcp-server}"
if [ ! -d "$BITWARDEN_DIR" ]; then
  echo "[bitwarden-mcp] Repository not found at $BITWARDEN_DIR" >&2
  echo "Set BITWARDEN_MCP_PATH or clone https://github.com/bitwarden/mcp-server.git" >&2
  exit 1
fi

if [ ! -f "$BITWARDEN_DIR/dist/index.js" ]; then
  echo "[bitwarden-mcp] dist/index.js missing. Run 'npm install' and 'npm run build' inside $BITWARDEN_DIR" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[bitwarden-mcp] Node.js is required" >&2
  exit 1
fi

if ! command -v bw >/dev/null 2>&1; then
  echo "[bitwarden-mcp] Bitwarden CLI (bw) is required" >&2
  exit 1
fi

if [ -z "${BW_SESSION:-}" ]; then
  echo "[bitwarden-mcp] Please export BW_SESSION (e.g. from 'bw unlock --raw') before launching." >&2
  exit 1
fi

cd "$BITWARDEN_DIR"
exec node dist/index.js
