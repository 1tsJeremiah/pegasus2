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
ARTIFACTS=()

RESTIC_BIN="${RESTIC_BIN:-restic}"
RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-${MINDSTACK_RESTIC_REPOSITORY:-}}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-${MINDSTACK_RESTIC_PASSWORD_FILE:-}}"
RESTIC_TAGS="${RESTIC_TAGS:-mindstack}"
if [[ -n "${RESTIC_BACKUP_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  RESTIC_BACKUP_ARGS_ARRAY=(${RESTIC_BACKUP_ARGS})
else
  RESTIC_BACKUP_ARGS_ARRAY=()
fi
if [[ -n "${RESTIC_FORGET_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  RESTIC_FORGET_ARGS_ARRAY=(${RESTIC_FORGET_ARGS})
else
  RESTIC_FORGET_ARGS_ARRAY=()
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[backup-mindstack] Docker is required to snapshot volumes." >&2
  exit 1
fi

restic_enabled() {
  [[ -n "$RESTIC_REPOSITORY" ]] && command -v "$RESTIC_BIN" >/dev/null 2>&1
}

run_restic() {
  if ! restic_enabled; then
    return
  fi

  local password_args=()
  if [[ -n "$RESTIC_PASSWORD_FILE" ]]; then
    password_args=(--password-file "$RESTIC_PASSWORD_FILE")
  fi

  "$RESTIC_BIN" --repo "$RESTIC_REPOSITORY" "${password_args[@]}" "$@"
}

upload_restic_artifacts() {
  if ! restic_enabled || [[ ${#ARTIFACTS[@]} -eq 0 ]]; then
    return
  fi

  echo "[backup-mindstack] Uploading ${#ARTIFACTS[@]} artifact(s) via restic"
  for artifact in "${ARTIFACTS[@]}"; do
    echo "[backup-mindstack] restic backup :: $artifact"
    run_restic backup --tag "$RESTIC_TAGS" "${RESTIC_BACKUP_ARGS_ARRAY[@]}" "$artifact"
  done

  if [[ ${#RESTIC_FORGET_ARGS_ARRAY[@]} -gt 0 ]]; then
    echo "[backup-mindstack] restic forget/prune :: ${RESTIC_FORGET_ARGS_ARRAY[*]}"
    run_restic forget "${RESTIC_FORGET_ARGS_ARRAY[@]}"
  fi
}

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

  ARTIFACTS+=("$BACKUP_ROOT/${ARCHIVE_PREFIX}-${label}-${TIMESTAMP}.tar.gz")
}

for volume in "${VOLUMES[@]}"; do
  backup_volume "$volume" "$volume"
done

echo "[backup-mindstack] Backup artifacts:"
find "$BACKUP_ROOT" -maxdepth 1 -type f -name "${ARCHIVE_PREFIX}-*-${TIMESTAMP}.tar.gz" -print

upload_restic_artifacts
