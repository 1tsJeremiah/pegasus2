#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

mkdir -p logs/codex

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

export CODEX_EMBED_MODEL="all-MiniLM-L6-v2"
export CODEX_VECTOR_DIM="384"

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" src/codex_integration/vector_cli.py stats --collection codex_agent --json logs/codex/stats.json
