# Mindstack Connectivity Guide

Mindstack is the local Pegasus memory stack (Chroma for development, migrating to Qdrant
for production). Keeping the stack reachable ensures Codex agents can continuously pull
context and submit new documents.

## Launch Workflow
- `scripts/codex/launch_mcp_stack.sh` sources `.env`, activates the project virtual
  environment, and waits for Mindstack to answer before starting MCP servers.
- The script exports Mindstack defaults (`CODEX_VECTOR_BASE_URL`, `CODEX_VECTOR_BACKEND`)
  based on `MINDSTACK_PROFILE`. Override these variables if the services run on a
  different host.
- When `RUN_VECTOR_SYNC=1` (default) the helper runs `scripts/codex/sync_documents.sh`
  to refresh collections before agents connect.

## Watchdog (Persistent Connectivity)
- `scripts/codex/mindstack_watchdog.sh` performs status checks on an interval and can
  restart the compose services automatically when Mindstack stops responding.
- `launch_mcp_stack.sh` starts the watchdog by default. Disable it with
  `START_MINDSTACK_WATCHDOG=0`.
- Tuning knobs:
  - `MINDSTACK_WATCHDOG_INTERVAL` (seconds between checks, default `60`).
  - `MINDSTACK_WATCHDOG_RESTART` (`1` to restart services, `0` to log only).
  - `MINDSTACK_COMPOSE_FILE` and `MINDSTACK_COMPOSE_SERVICES` to point at a custom
    compose manifest or service list.

## Health Checks
- Run `./.venv/bin/python src/codex_integration/vector_cli.py status` to confirm the
  active backend and available collections.
- The CLI accepts `CODEX_VECTOR_HTTP_RETRIES` and `CODEX_VECTOR_HTTP_RETRY_DELAY` to
  soften transient network errors against the Chroma HTTP API.
- Prometheus (`docker/docker-compose.yml`) scrapes container health endpoints so alerts
  can be added via Grafana.

## Recovery Steps
1. Verify Docker is running locally (`docker ps`).
2. Restart Mindstack services: `docker compose -f docker/docker-compose.yml up -d chroma qdrant meilisearch`.
3. Re-run the watchdog if it was disabled: `scripts/codex/mindstack_watchdog.sh`.
4. Re-seed collections when required: `scripts/codex/sync_documents.sh`.

Keep this guide close when adjusting Mindstack so Codex agents always have a consistent
memory hub.
