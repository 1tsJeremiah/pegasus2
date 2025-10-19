#!/usr/bin/env bash
set -euo pipefail

# Poll a PR until combined status is success, then attempt a squash merge.
# Requires GitHub CLI authenticated with write permissions.
#
# Usage: scripts/ci/watch_and_merge.sh <pr-number> [interval-seconds]

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <pr-number> [interval-seconds]" >&2
  exit 1
fi

PR_NUMBER="$1"
INTERVAL="${2:-60}"
REPO="1tsJeremiah/pegasus2"
MAX_MINUTES="90"

if ! command -v gh >/dev/null 2>&1; then
  echo "[watch] GitHub CLI (gh) not found." >&2
  exit 1
fi

echo "[watch] Watching PR #${PR_NUMBER} on ${REPO} every ${INTERVAL}s (timeout ${MAX_MINUTES}m)"

start_ts=$(date +%s)

while true; do
  now_ts=$(date +%s)
  elapsed=$(( (now_ts - start_ts) / 60 ))
  if (( elapsed > MAX_MINUTES )); then
    echo "[watch] Timeout after ${MAX_MINUTES} minutes." >&2
    exit 1
  fi

  head_sha=$(gh pr view "${PR_NUMBER}" -R "${REPO}" --json headRefOid --jq .headRefOid || echo "")
  if [[ -z "${head_sha}" ]]; then
    echo "[watch] Unable to fetch PR head SHA; retrying..."
    sleep "${INTERVAL}"
    continue
  fi

  state=$(gh api repos/${REPO}/commits/${head_sha}/status --jq .state || echo "")
  echo "[watch] $(date -Is) head=${head_sha:0:7} state=${state}"

  if [[ "${state}" == "success" ]]; then
    echo "[watch] Checks successful; attempting squash merge..."
    if gh pr merge "${PR_NUMBER}" -R "${REPO}" --squash -t "Production architecture upgrade (squash)"; then
      echo "[watch] Merge completed."
      exit 0
    else
      echo "[watch] Merge failed (permissions/policy). Posting a note..." >&2
      gh pr comment "${PR_NUMBER}" -R "${REPO}" -b "Automated watcher: checks passed but merge failed due to permissions or policy. Please squash-merge manually."
      exit 2
    fi
  fi

  sleep "${INTERVAL}"
done

