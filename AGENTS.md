# Repository Guidelines

## Project Structure & Module Organization
- `src/codex_integration/` hosts the Typer CLI (`vector_cli.py`) and ingestion entrypoints; group new commands under clear Typer sub-apps.
- `src/codex_vector/` holds ingestion pipelines, health checks, and storage helpers; extend existing utilities instead of cloning logic.
- `src/codex_keyword/` powers the Meilisearch companion; keep HTTP clients slim and reuse shared serializers.
- `docker/` provides compose files for dev and prod; keep service and env updates in sync between variants.
- `scripts/codex/` bundles automation (indexing, MCP stack, reporting); add new flows here so agents and CI share one surface.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` prepares the local virtual environment expected by scripts.
- `pip install -r requirements.txt` for runtime packages; append `-r requirements-dev.txt` when you need linting or tests.
- `docker-compose -f docker/docker-compose.dev.yml up -d` launches the Mindstack Core (Chroma) and Mindstack Index (Meilisearch); shut down with `... down` after validation.
- `./.venv/bin/python src/codex_integration/vector_cli.py setup` seeds collections, and `search "query"` or `status` provide quick smoke checks.
- `scripts/codex/launch_mcp_stack.sh` refreshes documents and starts the Codex MCP servers for end-to-end exercises.
- `scripts/codex/mindstack_watchdog.sh` keeps Mindstack reachable by polling `vector_cli status` and restarting compose services when needed.
- `scripts/codex/run_bitwarden_mcp.sh` launches the Bitwarden MCP server (requires `BW_SESSION` and a local clone at `~/bitwarden-mcp-server`; set `START_BITWARDEN_MCP=1` for the launch helper).
- `scripts/codex/run_google_mcp.sh` launches the Google Workspace MCP server in read-only mode (expects the `mcp-google` repo at `~/mcp-google` and OAuth secrets under `~/.config/mindstack/google/<profile>/`; enable via `START_GOOGLE_MCP=1`).

## Ingestion Utilities
- `scripts/codex/ingest_desktop_to_mindstack.py` ingests non-audio Desktop artifacts into the `codex_agent` collection (supports `--dry-run`).
- `scripts/codex/ingest_google_workspace.py` reads Gmail/Drive content using the OAuth tokens stored for the MCP server and indexes chunks into `gx_gmail_<profile>` / `gx_drive_<profile>`.

## Coding Style & Naming Conventions
- Target Python 3.8+ with four-space indentation, useful type hints, and docstrings on public entrypoints.
- Format with `black src/` and `isort src/`; lint via `flake8 src/` and type-check with `mypy src/`.
- Keep environment variables uppercase snake case (`CODEX_VECTOR_COLLECTION`, `CODEX_EMBED_MODEL`) and match CLI option names to Typer command groups.

## Testing Guidelines
- Author tests with `pytest` and `pytest-asyncio`; place new suites under `tests/` mirroring the source package layout.
- Run `pytest` plus `./.venv/bin/python src/codex_integration/vector_cli.py status` before pushing changes that affect ingestion or storage.
- Prefer lightweight fixtures in `tests/fixtures/` (create if needed) and avoid bundling large binaries in git.

## Commit & Pull Request Guidelines
- Use imperative commit subjects (“Add Qdrant heartbeat check”) and wrap extended descriptions at ~72 characters.
- Reference related issues (`Refs #123`) and note key commands executed during validation.
- PRs should summarize behavior changes, call out updated docs or env files, and include screenshots or logs when altering CLI output.

## Security & Configuration Tips
- Copy `.env.example` to `.env`, then set secrets such as `CODEX_MEILI_MASTER_KEY`, `CODEX_EMBED_MODEL`, and host/port overrides locally.
- Store tokens in your shell or secret manager; avoid committing credentials to compose files or scripts.
- Preserve named Docker volumes from `docker/` when reworking services to keep vector and keyword data intact.
