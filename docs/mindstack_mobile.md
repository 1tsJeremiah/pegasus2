# Mindstack Mobile Playbook

Mindstack is the Pegasus memory stack (Chroma vector store + Meilisearch keyword
index + MCP launch scripts). This guide documents how agents should refer to the
stack when the Codex client runs on an Android device via Termux.

## Terminology
- **Mindstack Core** – Chroma running on the desktop or a reachable host.
- **Mindstack Index** – Meilisearch keyword index that complements semantic
  search.
- **Mindstack Orchestrator** – The scripts under `scripts/codex/` that launch
  Docker, GitHub, Android ADB, and other MCP servers.
- **Mindstack Mobile** – Termux + Codex CLI on Android, using the one-tap widget
  described below.

Always refer to the memory stack as _Mindstack_ when prompting models. Mention
surfaces (Core, Index, Orchestrator) only when you need to call out a specific
service.

## Termux Environment
1. Install Termux and the Termux:Widget add-on.
2. Clone this repository under Termux (e.g. `~/codex-agent`).
3. Create the virtual environment and install requirements:
   ```bash
   cd ~/codex-agent
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements-termux.txt
   ```
4. Set the Codex API key in `~/.bashrc`:
   ```bash
   cat >>~/.bashrc <<'KEYS'
   export OPENAI_API_KEY="<mindstack-project-key>"
   export OPENAI_API_BASE="https://api.openai.com/v1"
   KEYS
   chmod 600 ~/.bashrc
   ```
5. Activate the environment as needed:
   ```bash
   source ~/.bashrc
   cd ~/codex-agent
   . .venv/bin/activate
   ```

## One-Tap Launcher
The widget calls `~/.shortcuts/tasks/start-codex.sh` (created by the automation).
The script:
- Sources `~/.bashrc` for the Mindstack credentials.
- Activates `~/codex-agent/.venv/`.
- Runs `codex --model gpt-5-codex --sandbox workspace-write` so agents can issue
  `/model`, `/approvals`, and other slash commands immediately.

After installing Termux:Widget:
1. Place the widget on the Android home screen.
2. Pick `tasks/start-codex.sh` when prompted.
3. Tap the widget to drop into Codex. Use slash commands to switch models or
   approvals, then ask for environment checks (e.g. `pwd`, `ls -1`).

## Mindstack Orchestrator on Mobile

### One-Tap Orchestrator
Use the Termux:Widget entry `tasks/start-mindstack-orchestrator.sh` to launch Mindstack servers with sensible defaults (`RUN_VECTOR_SYNC=1`, `START_ANDROID_ADB_MCP=1`, Docker/GitHub MCP off by default). Override any flag before tapping the widget if you need a different profile.
`~/run_codex_mcp.sh` wraps the MCP launch helper. Defaults:
- `RUN_VECTOR_SYNC=0`
- `START_DOCKER_MCP=0`
- `START_GITHUB_MCP=0`
- `START_ANDROID_ADB_MCP=0`

Override as needed before invoking the script:
```bash
START_ANDROID_ADB_MCP=1 ~/run_codex_mcp.sh
```

For desktop services (Chroma/Qdrant, Meilisearch, GitHub MCP), establish SSH
port forwards from the phone to the desktop before launching the stack so the
Mindstack Core endpoints resolve locally (e.g. tunnel `127.0.0.1:8000`).

## Agent Prompts
When documenting or prompting, prefer phrasing such as:
- "Query Mindstack for the latest deployment notes."
- "Use the Mindstack Index keyword search for filenames containing `docker`."
- "Launch the Mindstack Orchestrator with `RUN_VECTOR_SYNC=1` to refresh
  collections."

Avoid referring to "the Chroma/Meili stack"; the single name keeps memory and
instructions aligned.

## Useful Paths
- `~/codex-agent/scripts/codex/` – Mindstack Orchestrator scripts.
- `~/codex-agent/config/codex/` – Tool manifests referenced by Codex/Termux.
- `~/codex-agent/run_codex_mcp.sh` – Mobile-friendly launcher with defaults.
- `~/.shortcuts/tasks/start-codex.sh` – Widget entry point to Codex CLI.

Keep this document in sync when the automation changes, and ingest it into
Mindstack so agents always have the mobile workflow handy.
