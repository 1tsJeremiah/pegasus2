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
  source .env
  set +a
fi

: "${GOOGLE_PROFILE:=primary}"
export GOOGLE_PROFILE

: "${GOOGLE_CONFIG_DIR:=$HOME/.config/mindstack/google/$GOOGLE_PROFILE}"
export GOOGLE_CONFIG_DIR

mkdir -p "$GOOGLE_CONFIG_DIR"

if [ -z "${GOOGLE_OAUTH_CREDENTIALS:-}" ]; then
  CREDENTIAL_CANDIDATE="$GOOGLE_CONFIG_DIR/client_secret.json"
  if [ -f "$CREDENTIAL_CANDIDATE" ]; then
    export GOOGLE_OAUTH_CREDENTIALS="$CREDENTIAL_CANDIDATE"
  fi
fi

if [ -z "${GOOGLE_OAUTH_CREDENTIALS:-}" ]; then
  echo "[google-mcp] Missing Google OAuth credentials. Place client_secret.json in $GOOGLE_CONFIG_DIR or set GOOGLE_OAUTH_CREDENTIALS." >&2
  exit 1
fi

export GOOGLE_MCP_REPO="${GOOGLE_MCP_REPO:-$HOME/mcp-google}"

NODE_BIN="${NODE_BIN:-node}"

exec "$NODE_BIN" "$REPO_DIR/mindstack/google/google_workspace_readonly.mjs"
