#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

INDEX_NAME="${CODEX_MEILI_INDEX:-codex_os_search}"
python3 src/codex_keyword/meili_cli.py index-path \
  --index "$INDEX_NAME" \
  --include ".md" --include ".txt" --include ".py" --include ".conf" --include ".service" --include ".log" \
  --exclude-dir ".git" --exclude-dir "node_modules" --exclude-dir "__pycache__" --exclude-dir "venv" --exclude-dir ".venv" \
  . /etc
