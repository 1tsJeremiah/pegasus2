#!/usr/bin/env bash
set -euo pipefail

# Minimal rollback helper: checks out a given git ref and restarts services.
# Usage: bash scripts/deploy/rollback.sh <git-ref>

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <git-ref>" >&2
  exit 1
fi

TARGET_REF="$1"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if ! git rev-parse --verify --quiet "$TARGET_REF" >/dev/null; then
  echo "[rollback] ERROR: Unknown ref: $TARGET_REF" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[rollback] Working tree not clean. Commit/stash before rollback." >&2
  exit 1
fi

echo "[rollback] Checking out $TARGET_REF..."
git checkout -f "$TARGET_REF"

echo "[rollback] Restarting services..."
docker compose -f docker/docker-compose.yml up -d

echo "[rollback] Current commit: $(git rev-parse --short HEAD)"
echo "[rollback] Done. Verify health: python src/codex_integration/vector_cli.py status"

