# Warp Terminal Vector Database LangChain Integration

A comprehensive Docker-based solution for integrating vector databases with LangChain to enhance Warp Terminal with AI-powered semantic search, intelligent command assistance, and context-aware development workflows.

![Project Status](https://img.shields.io/badge/status-ready%20for%20testing-green)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🚀 Quick Start

```bash
# 1. Clone and navigate to the project
cd warp-vector-db-langchain

# 2. Start the vector database
docker-compose -f docker/docker-compose.dev.yml up -d

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# 5. Initialize the system
python src/warp_integration/vector_cli.py setup

# 6. Test semantic search
python src/warp_integration/vector_cli.py search "find large files"
```

## 🎯 Project Overview

This project provides a seamless integration between:
- **🗄️ Vector Databases** (Chroma/Qdrant) containerized with Docker
- **🔗 LangChain** for vector operations, embeddings, and retrieval
- **⚡ Warp Terminal** for AI-enhanced terminal experiences

### Key Features

- **🔍 Semantic Command Search**: Find commands by describing what you want to do
- **🤖 Intelligent Help System**: Get context-aware assistance for terminal operations
- **📚 Command Knowledge Base**: Learn and remember command patterns and usage
- **🐳 Docker-First**: Easy deployment with Docker and docker-compose
- **🔄 Multiple Vector DB Support**: Choose between Chroma (development) and Qdrant (production)
- **🎨 Rich Terminal UI**: Beautiful command-line interface with Rich library

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Warp Terminal                 │
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
- **Development**: Chroma (simple setup, great for prototyping)
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
- OpenAI API Key (for embeddings)

### Step-by-Step Installation

#### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd warp-vector-db-langchain

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

# Edit .env with your settings
OPENAI_API_KEY=your-openai-api-key-here
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

#### 3. Start Vector Database

**For Development (Chroma):**
```bash
docker-compose -f docker/docker-compose.dev.yml up -d
```

**For Production (Both Chroma and Qdrant):**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

#### 4. Initialize the System

```bash
# Setup initial command database
python src/warp_integration/vector_cli.py setup

# Verify installation
python src/warp_integration/vector_cli.py status
```

## 📚 Usage Examples

### Basic CLI Operations

```bash
# Alias for convenience
alias vcli="python src/warp_integration/vector_cli.py"

# Semantic search for commands
vcli search "find large files in directory"
vcli search "commit changes to git" --scores

# Get contextual help
vcli help "docker container logs"
vcli help "python virtual environment"

# Add new command knowledge
vcli add "kubectl get pods -n namespace" --source "k8s-docs" --category "kubernetes"

# Add structured command help
vcli add-help "rsync" "Synchronize files between locations" \
  -e "rsync -av source/ dest/" \
  -e "rsync -av --delete source/ dest/"

# Check system status
vcli status
```

### Python API Usage

```python
from examples.chroma_basic_example import ChromaVectorStore

# Initialize vector store
vector_store = ChromaVectorStore()

# Add documents
documents = ["How to use git rebase", "Docker container management"]
vector_store.add_documents(documents)

# Semantic search
results = vector_store.similarity_search("version control", k=3)
for doc in results:
    print(doc.page_content)
```

### Warp Terminal Integration

```yaml
# ~/.warp/workflows/vector-search.yaml
name: "Smart Command Search"
command: "python /path/to/vector_cli.py search \"{{query}}\""
description: "Find commands using AI-powered semantic search"
arguments:
  - name: query
    description: "Describe what you want to do"
    required: true
```

## 📁 Project Structure

```
warp-vector-db-langchain/
├── 🐳 docker/                     # Docker configurations
│   ├── docker-compose.yml         # Production setup (Chroma + Qdrant)
│   └── docker-compose.dev.yml     # Development setup (Chroma only)
├── 📄 docs/                       # Documentation
│   ├── vector_db_research.md      # Vector DB analysis
│   └── warp_integration_guide.md  # Warp Terminal integration
├── 🎯 examples/                   # Usage examples and demos
│   └── chroma_basic_example.py    # Basic Chroma integration
├── 🔧 src/                        # Source code
│   ├── langchain_integration/     # LangChain integration modules
│   └── warp_integration/          # Warp Terminal integration
│       └── vector_cli.py          # Main CLI tool
├── 📋 requirements.txt            # Python dependencies
├── 🔒 .env.example               # Environment variables template
└── 📖 README.md                  # This file
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
CHROMA_HOST=localhost                      # Chroma server host
CHROMA_PORT=8000                          # Chroma server port
QDRANT_HOST=localhost                      # Qdrant server host  
QDRANT_PORT=6333                          # Qdrant server port
VECTOR_COLLECTION=warp_terminal           # Collection name
```

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
# Run basic functionality test
python examples/chroma_basic_example.py

# Test CLI functionality
python src/warp_integration/vector_cli.py status
python src/warp_integration/vector_cli.py search "test query"

# Test Docker setup
docker-compose -f docker/docker-compose.dev.yml ps
curl http://localhost:8000/api/v1/heartbeat
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

Contributions are welcome! Please check out our [contributing guide](CONTRIBUTING.md).

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
- **[Warp Integration Guide](docs/warp_integration_guide.md)**: Complete guide to Warp Terminal integration strategies
- **[API Documentation](docs/api.md)**: Python API reference
- **[Deployment Guide](docs/deployment.md)**: Production deployment instructions

## 🗺️ Roadmap

- **Phase 1** ✅: Core vector database integration with Docker
- **Phase 2** ✅: Basic CLI tool and LangChain integration
- **Phase 3** ✅: Warp Terminal integration strategies
- **Phase 4** 🚧: Advanced features (multi-modal, team collaboration)
- **Phase 5** 📋: Plugin ecosystem and marketplace integration

## ⚖️ License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the excellent framework
- [Chroma](https://trychroma.com/) for the developer-friendly vector database
- [Qdrant](https://qdrant.tech/) for high-performance vector search
- [Warp Terminal](https://warp.dev/) for revolutionizing the terminal experience

---

**Ready to supercharge your terminal with AI? Get started now!** 🚀
