#!/usr/bin/env bash
set -euo pipefail

if ! command -v adb >/dev/null 2>&1; then
  echo "[android-adb-mcp] adb executable not found in PATH" >&2
  echo "Install Android Platform Tools or export PATH so 'adb' is discoverable." >&2
  exit 1
fi

exec npx -y @landicefu/android-adb-mcp-server "$@"
