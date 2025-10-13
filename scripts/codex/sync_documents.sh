#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

mkdir -p data/codex/official_docs logs/codex

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "[sync-documents] Missing .venv virtual environment. Run 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt' first." >&2
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

if [ -z "${CODEX_MEILI_API_KEY:-}" ]; then
  echo "[sync-documents] CODEX_MEILI_API_KEY is required. Set a rotated Meilisearch master key." >&2
  exit 1
fi

if command -v playwright >/dev/null 2>&1; then
  if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    playwright install chromium >/dev/null 2>&1
  fi
fi

# Ensure Mindstack Core (Chroma) is running
if docker compose version >/dev/null 2>&1; then
  docker compose -f docker/docker-compose.dev.yml up -d
else
  docker-compose -f docker/docker-compose.dev.yml up -d
fi

PYTHON="${PYTHON:-.venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
  echo "[sync-documents] Expected Python interpreter at $PYTHON" >&2
  exit 1
fi

"$PYTHON" -m src.codex_vector.ingest.official_docs
"$PYTHON" -m src.codex_vector.ingest.ubuntu_docs --collection ubuntu-docs
"$PYTHON" -m src.codex_vector.ingest.infra_docs --collection infra-docs

"$PYTHON" -m src.codex_vector.health --output logs/codex/health.json || true

"$PYTHON" src/codex_integration/vector_cli.py stats --collection codex_agent --json logs/codex/stats.json
