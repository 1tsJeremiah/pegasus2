# Codex Agent Integration Guide

This guide explains how to connect the LangChain-based vector database toolkit
with Codex agents. Everything here is platform-neutral—no external terminal
dependencies are required.

## 1. Prepare Environment

> **Tip**: If your environment does not provide the `python` alias, substitute `python3` in the commands below.

1. (Optional) Create a virtual environment if you plan to use the LangChain examples
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. (Optional) Copy `.env.example` to `.env` if you intend to run the LangChain notebooks or OpenAI-backed workflows
   ```bash
   cp .env.example .env
   echo 'OPENAI_API_KEY=<your key>' >> .env
   ```

## 2. Start the Vector Database

The project supports Chroma for local development.

```bash
cd docker
docker compose -f docker-compose.dev.yml up -d
```

Confirm the container is healthy:
```bash
docker ps --filter name=chroma
```

## 3. Use the Codex Vector CLI

Activate the project virtual environment and run the LangChain-aware CLI from the repo root:
```bash
source .venv/bin/activate
python src/codex_integration/vector_cli.py status
```

### Common commands
- `python src/codex_integration/vector_cli.py status` – Inspect the connection and collections
- `python src/codex_integration/vector_cli.py add --collection codex_agent "content" --source docs` – Store a snippet
- `python src/codex_integration/vector_cli.py search "deploy container" --collection codex_agent` – Semantic lookup
- `python src/codex_integration/vector_cli.py setup --collection codex_agent` – Seed baseline command help

These commands use LangChain's `Chroma` vector store client under the hood. By default the bundled manifests set `CODEX_EMBED_PROVIDER=hash`, which locks the CLI to deterministic Blake2b vectors. Set `CODEX_EMBED_MODEL` (and switch the provider to `huggingface` or `openai`) if you want higher quality embeddings, and adjust `CODEX_VECTOR_DIM` (default 384) when changing models.

To bulk ingest project documentation with a high-quality model, run:

```bash
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 python -m src.codex_vector.ingest.bootstrap
```

Use `--paths` to specify additional files or directories.

### Official references

```bash
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 python -m src.codex_vector.ingest.official_docs
```

This pulls the latest Codex-oriented tutorials from the OpenAI Cookbook repository, stores the raw text under `data/codex/official_docs/`, and tags every chunk with its source URL.

### Ubuntu production docs

```bash
python -m src.codex_vector.ingest.ubuntu_docs
```

The command downloads the Ubuntu 24.04 LTS manuals (server, desktop, Lubuntu) and Canonical platform guides (Ubuntu Pro, AWS, GCP). PDFs protected by Cloudflare are fetched with Playwright, so install the dependency once via `pip install playwright && playwright install chromium`. The ingestion pipeline hashes each chunk deterministically, so reruns simply refresh the existing records.

In production the nightly sync job (`scripts/codex/sync_documents.sh`) already runs both `ingest.official_docs` and `ingest.ubuntu_docs`. Cron triggers it at `02:30` local time (`crontab -l`), ensuring the `ubuntu-docs` collection stays aligned with the bundled manuals.

### Session resumes

```bash
PYTHONPATH=src python scripts/codex/publish_session_resume.py <session-id> --label <short-label> --snapshot "..." --follow "..."
```

Provide one or more `--snapshot` bullets to capture the human-facing summary. Optional `--follow` bullets record next steps.

The script writes a markdown file under `~/Documents/codex-resumes/` (for example `session-01999568.md`) and mirrors the same text into the `session-resumes` Chroma collection so agents can search it.

Add `PYTHONPATH=src` (or activate the project virtualenv) so the helper can import `codex_vector`.

### Codex configuration

A ready-to-use tool manifest lives at `config/codex/vector-cli.json`. Copy it into your Codex tools directory (for example `~/.codex/tools/vector-cli.json`) to register the CLI with the agent. Update the path or environment variables if your deployment differs.

If you want Codex to access Docker and GitHub alongside the vector CLI, drop in `config/codex/all-tools.json`. It combines the LangChain CLI, Docker MCP server, and GitHub MCP server with sensible defaults (`CODEX_EMBED_PROVIDER=hash`).

To boot everything in one shot, run `scripts/codex/launch_mcp_stack.sh`. The helper ensures Chroma is up, refreshes the vector collections through `scripts/codex/sync_documents.sh`, and starts the Docker/GitHub MCP servers (skipping GitHub if no token is configured). Control behaviour with environment variables such as `RUN_VECTOR_SYNC=0`, `START_DOCKER_MCP=0`, or `START_GITHUB_MCP=0`. Stop the services with `Ctrl+C` when you are done.

To enable Docker management, copy `config/codex/docker-mcp.json` and start `scripts/codex/run_docker_mcp.sh` in a separate terminal when needed.

For GitHub integration, copy `config/codex/github-mcp.json` and launch `scripts/codex/run_github_mcp.sh` (ensure `GITHUB_PAT` or `GITHUB_PERSONAL_ACCESS_TOKEN` is exported).

### Routine health check

```bash
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 python -m src.codex_vector.health --output logs/codex/health.json
```

The nightly sync job already runs this after ingestion; rerun it manually for an immediate status report.

### Collection statistics

```bash
python src/codex_integration/vector_cli.py stats --collection codex_agent --top 5
```

Provides document totals and most frequent metadata values; combine with `--json` to emit machine-readable reports.

For convenience run: `scripts/codex/report_stats.sh`.

## 4. Hook Into Codex

1. Ensure the vector CLI can reach the Chroma instance (use the `status` command).
2. Register the CLI as a tool in Codex by pointing to a wrapper script, e.g.:
   ```json
   {
     "tools": {
       "vector-cli": {
         "command": "python3",
         "args": ["src/codex_integration/vector_cli.py"],
         "env": {
           "CODEX_EMBED_MODEL": "${env:CODEX_EMBED_MODEL}"
         }
       }
     }
   }
   ```
3. Ask Codex to execute vector CLI commands as part of your workflows.

## 5. Troubleshooting

- `❌ Failed to connect to vector database`: confirm the Chroma container is running and ports are accessible.
- `⚠️ Embedding model failed`: ensure `CODEX_EMBED_MODEL` points to a local `sentence-transformers` model or unset it to use the hash fallback.

## 6. Next Steps

- Automate ingestion by pointing `add-docs` at project documentation folders.
- Extend the CLI with custom subcommands for your Codex agents.
- Configure Codex workflows to call the CLI automatically after deployments.
