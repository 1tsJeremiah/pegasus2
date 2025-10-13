#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_DIR"

BACKUP_ROOT="${BACKUP_ROOT:-$REPO_DIR/backups/mindstack}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
mkdir -p "$BACKUP_ROOT"

ARCHIVE_PREFIX="${ARCHIVE_PREFIX:-mindstack}"
ARCHIVE_PATH="$BACKUP_ROOT/${ARCHIVE_PREFIX}-${TIMESTAMP}"

VOLUMES=("chroma_data" "qdrant_data" "meili_data")

if ! command -v docker >/dev/null 2>&1; then
  echo "[backup-mindstack] Docker is required to snapshot volumes." >&2
  exit 1
fi

backup_volume() {
  local volume_name=$1
  local label=$2

  if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
    echo "[backup-mindstack] Skipping $volume_name (volume not found)"
    return
  fi

  echo "[backup-mindstack] Archiving $volume_name"
  docker run --rm \
    -v "${volume_name}":/data:ro \
    -v "${BACKUP_ROOT}":/backup \
    alpine:3.20 \
    sh -c "cd /data && tar -czf /backup/${ARCHIVE_PREFIX}-${label}-${TIMESTAMP}.tar.gz ."
}

for volume in "${VOLUMES[@]}"; do
  backup_volume "$volume" "$volume"
done

echo "[backup-mindstack] Backup artifacts:"
find "$BACKUP_ROOT" -maxdepth 1 -type f -name "${ARCHIVE_PREFIX}-*-${TIMESTAMP}.tar.gz" -print
