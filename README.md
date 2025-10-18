# Codex Agent Vector Database LangChain Integration

A comprehensive Docker-based solution for integrating vector databases with LangChain to enhance Codex Agent with AI-powered semantic search, intelligent command assistance, and context-aware development workflows.

![Project Status](https://img.shields.io/badge/status-ready%20for%20testing-green)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Quick Start

> **Note**: Replace `python` with `python3` if your environment does not provide the `python` alias.

```bash
# 1. Clone and navigate to the project
cd vector-db-langchain

# 2. Start the vector database and keyword index
docker-compose -f docker/docker-compose.dev.yml up -d

# 3. Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. (Optional) Set up your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# 5. Initialize the system with the LangChain CLI
./.venv/bin/python src/codex_integration/vector_cli.py setup

# 6. Test semantic search
./.venv/bin/python src/codex_integration/vector_cli.py search "find large files"
```

## 🧠 Mindstack (Pegasus Memory)

Mindstack is the local Pegasus memory stack that bundles the Chroma vector store (transitioning to Qdrant), the Meilisearch keyword index, and the supporting MCP launch scripts. When agents refer to "Mindstack" they can assume the full package is available: vector search, keyword lookup, and the orchestration helpers that keep them in sync.

- **Mindstack Core (Chroma → Qdrant)** powers local development by default. Set `MINDSTACK_PROFILE=production` (or override `CODEX_VECTOR_BACKEND=qdrant`) to promote Qdrant while the migration is underway.
- **Mindstack Index (Meilisearch)** surfaces fast keyword matches across the filesystem and curated documents.
- **Mindstack Observability** layers Prometheus + cAdvisor for metrics and ships a snapshot helper for persistent volumes.
- **Mindstack Orchestrator (MCP scripts)** launches Docker, GitHub, Android ADB, and other optional servers so Codex can automate the environment.
- **Mindstack Reliability**: `scripts/codex/launch_mcp_stack.sh` now waits for the stack to answer before starting MCP servers and boots `scripts/codex/mindstack_watchdog.sh` to keep connections healthy.

Mindstack is the preferred name to use in playbooks, prompts, and documentation—agents do not need to reference "the Chroma/Meili stack" explicitly.

Refer to `docs/mindstack_connectivity.md` for operational notes on keeping Mindstack reachable.

## 🎯 Project Overview

This project provides a seamless integration between:
- **🧠 Mindstack Vector Layer** (Chroma for development, Qdrant for scale) containerized with Docker
- **🔗 LangChain** for vector operations, embeddings, and retrieval
- **⚡ Codex Agent** for AI-enhanced terminal experiences

### Key Features

- **🔍 Semantic Command Search**: Find commands by describing what you want to do
- **🤖 Intelligent Help System**: Get context-aware assistance for terminal operations
- **📚 Command Knowledge Base**: Learn and remember command patterns and usage
- **🐳 Docker-First**: Easy deployment with Docker and docker-compose
- **🔄 Mindstack Flexibility**: Choose the Mindstack Core (Chroma) for development or swap in Qdrant for production scale
- **🎨 Rich Terminal UI**: Beautiful command-line interface with Rich library
- **📊 Collection Analytics**: Built-in stats command and nightly reports surface top sources and document trends
- **🎯 Embedding Flexibility**: Prefers `sentence-transformers` models when available and falls back to Blake2b-derived vectors for fully offline use
- **♻️ Stable Doc IDs**: Opt-in metadata-derived IDs for clean document overwrites (`CODEX_VECTOR_DOC_ID_FIELDS`)
- **⚙️ Adaptive Qdrant Transport**: Prefers gRPC for ingestion/search throughput (`CODEX_QDRANT_USE_GRPC=0` forces HTTP)
- **⚡ Keyword Search Companion**: Optional Meilisearch index delivers lightning-fast filename and content matches across the OS
- **📈 Observability Suite**: Prometheus + Grafana containers for dashboards and alerting

### Preloaded Collections
- `codex_agent`: OpenAI Codex cookbook excerpts
- `ubuntu-docs`: Offline Ubuntu server administration references
- `infra-docs`: Cloudflare Tunnels, Pi-hole Docker, Traefik (Docker provider + DNS challenge), and Docker Compose official docs

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Codex Agent                 │
│  ┌─────────────────────────────────────┤
│  │ 🔍 Semantic Search                  │
│  │ 🤖 AI Command Assistant             │
│  │ 📚 Context-Aware Help               │
│  │ ⚙️  CLI Tools (vector-cli)           │
│  └─────────────────┬───────────────────┤
└────────────────────┼───────────────────┘
                     │
       ┌─────────────▼─────────────┐
       │      LangChain Layer      │
       │ ┌───────────────────────┐ │
       │ │ 🧠 OpenAI Embeddings   │ │
       │ │ 📄 Document Processing │ │
       │ │ 🔄 Vector Operations   │ │
       │ │ 🎯 Similarity Search   │ │
       │ └───────────────────────┘ │
       └─────────────┬─────────────┘
                     │
       ┌─────────────▼─────────────┐
       │    Vector Database        │
       │     (Docker)              │
       │ ┌───────────────────────┐ │
       │ │ 🔹 Chroma (Dev)        │ │
       │ │ 🔸 Qdrant (Prod)      │ │
       │ │ 💾 Persistent Storage │ │
       │ └───────────────────────┘ │
       └───────────────────────────┘
```

## 📋 Research Results

### ✅ Vector Database Analysis Complete

| Database | Development | Production | LangChain Support | Docker Ready |
|----------|-------------|------------|-------------------|---------------|
| **Chroma** ⭐ | ✅ Excellent | ✅ Good | ✅ Full Support | ✅ Ready |
| **Qdrant** ⭐ | ✅ Good | ✅ Excellent | ✅ Full Support | ✅ Ready |
| **Weaviate** | ✅ Good | ✅ Excellent | ✅ Full Support | ⚠️ Complex |
| **Milvus** | ⚠️ Complex | ✅ Excellent | ✅ Full Support | ⚠️ Complex |
| **FAISS** | ✅ Good | ⚠️ Limited | ✅ Good | ➖ No Persistence |

**✅ Recommendations**:
- **Development**: Mindstack Core (Chroma) – simple setup, great for prototyping
- **Production**: Qdrant (enterprise features, high performance)

### ✅ LangChain Integration Complete

All major vector stores support:
- ✅ Document ingestion and similarity search
- ✅ Metadata filtering and advanced queries
- ✅ Async operations for performance
- ✅ Batch operations and streaming

## 🛠️ Installation & Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Optional: install `sentence-transformers` and download a local model (e.g., `pip install sentence-transformers` and `CODEX_EMBED_MODEL=all-MiniLM-L6-v2`) for high-quality embeddings

### Step-by-Step Installation

#### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd vector-db-langchain

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings (only needed if you plan to use LangChain notebooks or cloud embeddings)
OPENAI_API_KEY=your-openai-api-key-here
CHROMA_HOST=localhost
CHROMA_PORT=8000
CODEX_EMBED_MODEL=all-MiniLM-L6-v2
CODEX_VECTOR_DIM=384
```

#### 3. Start Vector Database

**For Development (Mindstack Core):**
```bash
docker-compose -f docker/docker-compose.dev.yml up -d
```

**For Production (Both Chroma and Qdrant):**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

#### 4. Initialize the System

```bash
# Setup initial command database (LangChain-enabled CLI)
./.venv/bin/python src/codex_integration/vector_cli.py setup

# Optional: re-embed with a local sentence-transformers model
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 ./.venv/bin/python -m src.codex_vector.ingest.bootstrap

# Verify installation
./.venv/bin/python src/codex_integration/vector_cli.py status
```

## 📚 Usage Examples

### Basic CLI Operations

```bash
# Alias for convenience
alias vcli="./.venv/bin/python src/codex_integration/vector_cli.py"

# Seed or refresh the built-in collection
vcli setup

# Add new command knowledge (auto-creates the collection with --create)
vcli add codex_agent "kubectl get pods -n namespace" --source k8s-docs

# Bulk load snippets from a file (one per line)
vcli upsert codex_agent --file snippets.txt --tag docs --create

# Run a similarity search
vcli search codex_agent "deploy container"

# Inspect collections and connection status
vcli status
```

### Embedding options

- Set `CODEX_EMBED_MODEL` to the name or path of a local `sentence-transformers` model to enable high-quality embeddings.
- Adjust `CODEX_VECTOR_DIM` when you change models or want a different deterministic fallback size (default 384).
- The shipped manifests set `CODEX_EMBED_PROVIDER=hash`, so the CLI sticks to deterministic Blake2b vectors unless you override the provider (e.g., `huggingface`, `openai`).
- If no higher fidelity model is configured the CLI uses Blake2b-derived vectors so everything continues to work offline.

### Bulk ingestion

Use the bootstrap helper to ingest key project docs (or provide your own paths):

```bash
python -m src.codex_vector.ingest.bootstrap \
  --paths README.md docs/codex_integration_guide.md docs/vector_db_research.md \
  src/codex_integration/vector_cli.py src/codex_vector/client.py
```

The script splits content into overlapping chunks, attaches metadata, and stores it in the configured collection.

### Official Codex documentation

Fetch the latest official examples from the OpenAI Cookbook and ingest them automatically:

```bash
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 python -m src.codex_vector.ingest.official_docs
```

Fetched source material is saved under `data/codex/official_docs/` for auditing, and each chunk is tagged with its originating URL.

### Codex tool manifest

Copy `config/codex/vector-cli.json` into your Codex configuration (for example `~/.codex/tools/vector-cli.json`) so the agent can invoke the CLI directly. Adjust the `command`, `args`, or environment block if you relocate the repository.

Need the full toolbox? `config/codex/all-tools.json` bundles the LangChain CLI, Docker MCP server, and GitHub MCP server behind one manifest so Codex can orchestrate containers, repositories, and the knowledge base without extra wiring.

### Agent stack helper

Run `scripts/codex/launch_mcp_stack.sh` to refresh the vector collections (via `sync_documents.sh`) and launch the MCP servers. Tweak behaviour with env vars such as `RUN_VECTOR_SYNC=0`, `START_DOCKER_MCP=0`, or `START_GITHUB_MCP=0`. The script:

```bash
RUN_VECTOR_SYNC=1 scripts/codex/launch_mcp_stack.sh
```

- Boots the Mindstack Core (Chroma) container if required and runs the ingestion/health pipeline.
- Starts the Docker MCP server (unless it is already running).
- Starts the GitHub MCP server when `GITHUB_PAT`/`GITHUB_PERSONAL_ACCESS_TOKEN` is present.
- Defaults to `CODEX_EMBED_PROVIDER=hash`; override the variable before launching if you prefer HuggingFace or OpenAI embeddings.

Press `Ctrl+C` to shut down the background MCP servers that the helper launches.

### Docker MCP server

Add Docker management capabilities to Codex:

- Manifest: `config/codex/docker-mcp.json` (copy into `~/.codex/tools/` alongside the vector CLI manifest).
- Runtime: `scripts/codex/run_docker_mcp.sh` (wraps the local `.venv` and launches `mcp-server-docker`).

Start the server in a dedicated terminal when you need Docker access:

```bash
scripts/codex/run_docker_mcp.sh
```

### GitHub MCP server

- Manifest: `config/codex/github-mcp.json` (copy into `~/.codex/tools/`).
- Runtime: `scripts/codex/run_github_mcp.sh` (expects `GITHUB_PAT` or `GITHUB_PERSONAL_ACCESS_TOKEN` in the environment).

Launch when you want Codex to interact with repositories:

```bash
GITHUB_PAT=ghp_xxx scripts/codex/run_github_mcp.sh
```

### Android ADB MCP server

- Manifest: `config/codex/android-adb-mcp.json` (copy into your MCP host's tooling directory).
- Runtime: `scripts/codex/run_android_adb_mcp.sh` (requires the Android Platform Tools so `adb` is in PATH).
- Optionally disable automatic startup by exporting `START_ANDROID_ADB_MCP=0` before running `scripts/codex/launch_mcp_stack.sh`.

Start it manually when you need to automate a connected device:

```bash
scripts/codex/run_android_adb_mcp.sh
```

### Automated health checks

Validate the stack at any time (the nightly sync script runs this after fetching docs):

```bash
CODEX_EMBED_MODEL=all-MiniLM-L6-v2 python -m src.codex_vector.health
```

JSON output is written to STDOUT (or `logs/codex/health.json` when triggered by the cron job) and verifies query coverage plus the presence of key resources.

### Collection statistics

```bash
./.venv/bin/python src/codex_integration/vector_cli.py stats codex_agent --top 5
```

The command reports total documents and the most common sources, doc IDs, and titles. Use `--json <path>` to export machine-readable summaries (the nightly sync job writes `logs/codex/stats.json`).

### Python API Usage

```python
from codex_vector.client import CodexVectorClient

client = CodexVectorClient()
client.upsert(
    "codex_agent",
    ["How to use git rebase", "Docker container management"],
    metadata_items=[{"source": "docs"}, {"source": "docs"}],
    create_collection=True,
)

for match in client.query_results("codex_agent", "version control", limit=3):
    print(match["document"], match["metadata"])
```

### Keyword Search CLI

```bash
# Create the Meilisearch index (idempotent)
python src/codex_keyword/meili_cli.py create --index codex_os_search

# Index local repository files and selected system paths
python src/codex_keyword/meili_cli.py index-path \
  --index codex_os_search \
  --include .md --include .conf --include .py --include .service \
  . /etc

# Execute a keyword search across the indexed corpus
python src/codex_keyword/meili_cli.py search "restart networking" --limit 5
```

### Codex Agent Integration

```yaml
# ~/.codex/workflows/vector-search.yaml
name: "Smart Command Search"
command: "python3 /path/to/cli.py search \"{{query}}\""
description: "Find commands using AI-powered semantic search"
arguments:
  - name: query
    description: "Describe what you want to do"
    required: true
```

## 📁 Project Structure

```
vector-db-langchain/
├── 🐳 docker/                     # Docker configurations
│   ├── docker-compose.yml         # Production setup (Chroma + Qdrant)
│   └── docker-compose.dev.yml     # Development setup (Mindstack Core only)
├── 📄 docs/                       # Documentation
│   ├── vector_db_research.md      # Vector DB analysis
│   └── codex_integration_guide.md  # Codex Agent integration
├── 🔧 src/                        # Source code
│   ├── codex_vector/              # Codex Agent tooling and ingestion helpers
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── constants.py
│   │   ├── embeddings.py
│   │   ├── health.py
│   │   └── ingest/
│   │       ├── bootstrap.py
│   │       ├── infra_docs.py
│   │       ├── official_docs.py
│   │       └── ubuntu_docs.py
│   ├── codex_integration/         # LangChain-based CLI
│   │   ├── __init__.py
│   │   └── vector_cli.py
│   ├── codex_keyword/             # Meilisearch keyword CLI and helpers
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── meili_cli.py
├── ⚙️ scripts/                    # Automation scripts
│   └── codex/
│       ├── launch_mcp_stack.sh    # Orchestrate vector sync and MCP servers
│       ├── publish_session_resume.py # Persist searchable engagement summaries
│       ├── report_stats.sh        # On-demand collection statistics
│       ├── run_android_adb_mcp.sh # Launch Android ADB MCP server
│       ├── run_docker_mcp.sh      # Launch Docker MCP server
│       ├── run_github_mcp.sh      # Launch GitHub MCP server
│       ├── sync_documents.sh      # Nightly doc sync + health report
│       └── index_keyword.sh       # Populate Meilisearch with repo + OS files
├── 🗂 config/
│   ├── codex/vector-cli.json      # Manifest for registering the CLI tool
│   ├── codex/all-tools.json       # Aggregated tool manifest for agents
│   ├── codex/android-adb-mcp.json # Android ADB MCP manifest
│   ├── codex/docker-mcp.json      # Docker MCP manifest
│   ├── codex/github-mcp.json      # GitHub MCP manifest
│   └── codex/meili-cli.json       # Keyword search manifest
├── 📋 requirements.txt            # Runtime dependencies
├── 📄 requirements-dev.txt        # Development and linting dependencies
├── 🔒 .env.example                # Environment variables template
└── 📖 README.md                # This file
```

## 🎨 Features in Detail

### 🔍 Semantic Command Search

Instead of remembering exact syntax, describe what you want to do:

```bash
# Traditional approach
find . -name "*.py" -type f -exec grep -l "import numpy" {} \;

# Semantic approach
vcli search "find python files that import numpy"
# Returns the exact command above with explanation
```

### 🤖 Context-Aware Help

Get help that adapts to your current project and directory:

```bash
# In a Python project
vcli help "run tests"
# Returns: pytest, python -m pytest, tox

# In a Node.js project  
vcli help "run tests"
# Returns: npm test, yarn test, jest
```

### 📚 Learning Command Patterns

The system learns from your usage and builds a knowledge base:

```bash
# System learns that you often use these commands together
git add .
git commit -m "message"
git push

# Later suggests workflow
vcli help "commit and push changes"
# Returns: Suggests creating a workflow or alias
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your-openai-api-key        # For embeddings

# Optional (with defaults)
CHROMA_HOST=localhost                      # Mindstack Core (Chroma) host
CHROMA_PORT=8000                          # Mindstack Core (Chroma) port
QDRANT_HOST=localhost                      # Qdrant server host  
QDRANT_PORT=6333                          # Qdrant server port
CODEX_VECTOR_COLLECTION=codex_agent     # Collection name
CODEX_MEILI_URL=http://127.0.0.1:7700    # Meilisearch base URL
CODEX_MEILI_API_KEY=dev-master-key-123456 # Meilisearch API key (optional for dev)
CODEX_MEILI_INDEX=codex_os_search        # Keyword index name
CODEX_QDRANT_USE_GRPC=1                 # Prefer Qdrant gRPC transport (set 0 to disable)
CODEX_QDRANT_GRPC_PORT=6334             # Override gRPC port (auto +1 from HTTP port)
CODEX_VECTOR_UPSERT_BATCH=128           # Maximum docs per upsert call
CODEX_VECTOR_EXISTING_ID_BATCH=256      # Maximum ids per existence lookup
CODEX_VECTOR_DOC_ID_FIELDS=source,position  # Metadata keys used to derive stable doc IDs
CODEX_VECTOR_OVERWRITE_EXISTING=0       # Re-upsert documents when IDs already exist
RESTIC_REPOSITORY=s3:s3.amazonaws.com/...    # Optional restic repo for backup_mindstack.sh
RESTIC_PASSWORD_FILE=~/.config/restic/pass   # Restic password file (or export RESTIC_PASSWORD)
RESTIC_BACKUP_ARGS="--host mindstack"        # Additional flags for restic backup
RESTIC_FORGET_ARGS="--keep-last 7 --prune"   # Retention policy passed to restic forget
TRAEFIK_DASHBOARD_USERS=admin:$$2y$$...      # htpasswd entry exported from Bitwarden (optional)
GRAFANA_ADMIN_USER=grafana                  # Grafana admin username
GRAFANA_ADMIN_PASSWORD=strong-password      # Grafana admin password (store in Bitwarden)
```

## 🛡️ Backups & Observability

- `scripts/codex/backup_mindstack.sh` keeps the local tarball flow and, when `RESTIC_REPOSITORY` is set (plus credentials), automatically uploads each artifact via `restic backup` and applies optional retention with `RESTIC_FORGET_ARGS`.
- `monitoring/prometheus.yml` now scrapes cAdvisor, Qdrant, and Meilisearch metrics so dashboards can include vector-store health alongside container stats.
- Combine both by running `RESTIC_REPOSITORY=s3:... scripts/codex/backup_mindstack.sh` under a cron/systemd timer and pointing Grafana at Prometheus for seatbelt monitoring.

### Docker Customization

```yaml
# docker/docker-compose.dev.yml - Development settings
services:
  chroma:
    environment:
      - CHROMA_LOG_LEVEL=DEBUG              # Verbose logging
      - CHROMA_SERVER_CORS_ALLOW_ORIGINS=["*"] # Allow all origins
```

## 🧪 Testing

```bash
# Run CLI smoke checks
./.venv/bin/python src/codex_integration/vector_cli.py status
./.venv/bin/python src/codex_integration/vector_cli.py search "test query"

# Test Docker setup
docker-compose -f docker/docker-compose.dev.yml ps
curl http://localhost:8000/api/v2/heartbeat
```

## 🚀 Advanced Usage

### Batch Operations

```python
# Add multiple documents efficiently
vector_store = ChromaVectorStore()
documents = load_documentation_files()
vector_store.add_documents(documents, batch_size=100)
```

### Custom Embeddings

```python
from sentence_transformers import SentenceTransformer
from langchain.embeddings import HuggingFaceEmbeddings

# Use local embeddings model
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)
vector_store = ChromaVectorStore(embeddings=embeddings)
```

### Multi-Tenancy

```python
# Separate collections for different projects
project_store = ChromaVectorStore(collection_name="project_alpha")
team_store = ChromaVectorStore(collection_name="team_shared")
```

## 🔍 Troubleshooting

### Common Issues

**Docker Connection Issues**:
```bash
# Check if containers are running
docker-compose -f docker/docker-compose.dev.yml ps

# View container logs
docker-compose -f docker/docker-compose.dev.yml logs chroma

# Restart containers
docker-compose -f docker/docker-compose.dev.yml restart
```

**OpenAI API Issues**:
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API connectivity
python -c "from openai import OpenAI; print(OpenAI().models.list())"
```

**Python Dependencies**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check for conflicts
pip check
```

## 🤝 Contributing

Contributions are welcome! Please review the [Repository Guidelines](AGENTS.md) before opening a PR.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black src/
isort src/

# Lint
flake8 src/
mypy src/
```

## 📄 Documentation

- **[Vector Database Research](docs/vector_db_research.md)**: Detailed analysis of vector database options
- **[Codex Integration Guide](docs/codex_integration_guide.md)**: Complete guide to Codex Agent integration strategies
- **[API Documentation](docs/api.md)**: Python API reference
- **[Deployment Guide](docs/deployment.md)**: Production deployment instructions

## 🗺️ Roadmap

- **Phase 1** ✅: Core vector database integration with Docker
- **Phase 2** ✅: Basic CLI tool and LangChain integration
- **Phase 3** ✅: Codex Agent integration strategies
- **Phase 4** 🚧: Advanced features (multi-modal, team collaboration)
- **Phase 5** 📋: Plugin ecosystem and marketplace integration

## ⚖️ License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the excellent framework
- [Chroma](https://trychroma.com/) for the developer-friendly Mindstack Core vector database
- [Qdrant](https://qdrant.tech/) for high-performance vector search
- Codex CLI (internal docs) for agent orchestration guidance

---

**Ready to supercharge your terminal with AI? Get started now!** 🚀
