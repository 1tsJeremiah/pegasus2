# Repository Guidelines

## Project Structure & Module Organization
- `src/codex_integration/` holds the Typer CLI (`vector_cli.py`); keep new commands modular and document flags inline.
- `src/codex_vector/` provides ingestion, health, and bootstrap helpers reused by agents; extend packages rather than creating ad-hoc scripts.
- `src/codex_keyword/` wraps Meilisearch interactions for keyword lookup—keep it focused on text extraction and HTTP calls.
- `docker/` contains compose files for Chroma-only dev and dual-store prod; update env references in both when adjusting services.
- `scripts/codex/` centralizes automation entry points; add new workflows here so agents can invoke them consistently.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` prepares the environment expected by bundled scripts.
- `pip install -r requirements.txt` pulls runtime, formatting, and pytest tooling in one step.
- `docker-compose -f docker/docker-compose.dev.yml up -d` starts the dev stack (Chroma + Meilisearch); stop with `docker-compose ... down` after testing.
- `./.venv/bin/python src/codex_integration/vector_cli.py setup` seeds collections; rerun after ingest or schema edits.
- `python src/codex_keyword/meili_cli.py index-path .` or `scripts/codex/index_keyword.sh` builds the keyword index—rerun whenever system docs change.
- `scripts/codex/launch_mcp_stack.sh` refreshes documents and launches MCP servers; set `RUN_VECTOR_SYNC=0` for a quick start.

## Coding Style & Naming Conventions
- Target Python 3.8+ with 4-space indentation and descriptive type hints.
- Run `black src/` and `isort src/` before committing; CI enforces these formats.
- Lint with `flake8 src/` and type-check via `mypy src/`; address warnings instead of silencing them.
- Environment variables follow uppercase snake case (`CODEX_VECTOR_COLLECTION`, `CODEX_EMBED_MODEL`, `CODEX_MEILI_URL`); keep CLI command names consistent with Typer groups.

## Testing Guidelines
- Place new tests under `tests/`, mirroring the source package; use async fixtures when exercising LangChain clients.
- Execute `pytest` locally and include at least one CLI smoke check (`./.venv/bin/python src/codex_integration/vector_cli.py status`) when collections change.
- Store reusable sample inputs under `data/fixtures/` and document large assets in `.gitignore`.

## Commit & Pull Request Guidelines
- Write imperative commit subjects (“Add Qdrant heartbeat check”) and wrap bodies at 72 characters.
- Note related issues (`Refs #123`) plus the commands you ran; call out doc updates (`README.md`, `.env.example`, manifests) in the PR description.
- Request reviewers for each affected area (`CLI`, `ingest`, `docker`) and wait for automated checks before merging.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and set `CODEX_VECTOR_COLLECTION`, embedding variables, Meilisearch keys, and secrets locally only (Bitwarden export script reads `CODEX_MEILI_MASTER_KEY`).
- Prefer shell exports or local keychains for API tokens; avoid persisting credentials in scripts or compose files.
- Keep Docker volumes named as in `docker/` configs to preserve collection data across upgrades.
