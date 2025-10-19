#!/usr/bin/env bash
set -euo pipefail

# Lightweight staging deploy helper.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

# Defaults appropriate for staging
export MINDSTACK_PROFILE="${MINDSTACK_PROFILE:-dev}"
export CODEX_VECTOR_BACKEND="${CODEX_VECTOR_BACKEND:-chroma}"
if [[ "${CODEX_VECTOR_BACKEND}" == "qdrant" ]]; then
  export CODEX_VECTOR_BASE_URL="${CODEX_VECTOR_BASE_URL:-http://127.0.0.1:6333}"
else
  export CODEX_VECTOR_BASE_URL="${CODEX_VECTOR_BASE_URL:-http://127.0.0.1:8000}"
fi
export CODEX_MEILI_URL="${CODEX_MEILI_URL:-http://127.0.0.1:7700}"

if [[ -z "${CODEX_MEILI_API_KEY:-}" ]]; then
  echo "[staging] ERROR: CODEX_MEILI_API_KEY is required (set in environment or .env)" >&2
  exit 1
fi

echo "[staging] Using backend=${CODEX_VECTOR_BACKEND} base=${CODEX_VECTOR_BASE_URL} meili=${CODEX_MEILI_URL}"

echo "[staging] Pulling images..."
docker compose -f docker/docker-compose.yml pull

echo "[staging] Starting services..."
docker compose -f docker/docker-compose.yml up -d

PY_BIN="python3"
if [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
  PY_BIN="$REPO_DIR/.venv/bin/python"
fi

CLI="$REPO_DIR/src/codex_integration/vector_cli.py"

echo "[staging] Waiting for vector backend..."
retries=${MINDSTACK_READY_RETRIES:-12}
delay=${MINDSTACK_READY_DELAY:-5}
for ((i=1;i<=retries;i++)); do
  if "$PY_BIN" "$CLI" status >/dev/null 2>&1; then
    echo "[staging] Vector backend is reachable."
    break
  fi
  echo "[staging] Not ready yet (attempt $i/${retries}); retrying in ${delay}s..."
  sleep "$delay"
done

echo "[staging] Meilisearch health:"
curl -fsS "${CODEX_MEILI_URL}/health" || true

echo "[staging] Done. Review logs if needed: docker compose -f docker/docker-compose.yml logs -f"

