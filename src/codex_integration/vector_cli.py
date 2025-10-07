#!/usr/bin/env python3
"""LangChain-integrated vector CLI for Codex agents.

This tool wraps the Chroma vector database using LangChain best practices so
agents can run persistent semantic search and ingestion workflows. It mirrors
the capabilities of the lightweight HTTP client used by the ingestion tools
while leveraging LangChain abstractions for embeddings and retrieval.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import typer

SRC_ROOT = Path(__file__).resolve().parent.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from chromadb import HttpClient
    from chromadb.api.client import ClientAPI
    from chromadb.errors import NotFoundError
except ImportError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "chromadb is required. Activate the vector-db-langchain virtualenv and "
        "run 'pip install -r requirements.txt'"
    ) from exc

try:
    from langchain_core.embeddings import Embeddings
except ImportError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "langchain-core is required. Activate the vector-db-langchain "
        "virtualenv and install dependencies."
    ) from exc

try:  # Prefer the dedicated package first
    from langchain_chroma import Chroma
except Exception:  # pragma: no cover - fallback
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "langchain vectorstore integrations are required. Activate the "
            "vector-db-langchain virtualenv and install dependencies."
        ) from exc

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except Exception:  # pragma: no cover - optional dependency
    HuggingFaceEmbeddings = None  # type: ignore

try:  # Optional OpenAI support
    from langchain_openai import OpenAIEmbeddings
except Exception:  # pragma: no cover - optional dependency
    OpenAIEmbeddings = None  # type: ignore

from codex_vector.constants import DEFAULT_SETUP_SNIPPETS
from codex_vector.embeddings import DEFAULT_DIMENSION, generate_embedding

app = typer.Typer(help="Persistent LangChain wrapper for the Codex vector database")

DEFAULT_BASE_URL = os.environ.get("CODEX_VECTOR_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TENANT = os.environ.get("CODEX_VECTOR_TENANT", "default_tenant")
DEFAULT_DATABASE = os.environ.get("CODEX_VECTOR_DB", "default_database")
DEFAULT_COLLECTION = os.environ.get("CODEX_VECTOR_COLLECTION", "codex_agent")
DEFAULT_DIM = int(os.environ.get("CODEX_VECTOR_DIM", str(DEFAULT_DIMENSION)))
DEFAULT_TAG = os.environ.get("CODEX_VECTOR_DEFAULT_TAG", "codex")


@dataclass
class AppConfig:
    base_url: str
    tenant: str
    database: str
    collection: str


@app.callback()
def _init(
    ctx: typer.Context,
    base_url: str = typer.Option(
        DEFAULT_BASE_URL,
        "--base-url",
        envvar="CODEX_VECTOR_BASE_URL",
        help="Chroma server base URL (default: http://127.0.0.1:8000)",
    ),
    tenant: str = typer.Option(
        DEFAULT_TENANT,
        "--tenant",
        envvar="CODEX_VECTOR_TENANT",
        help="Chroma tenant identifier",
    ),
    database: str = typer.Option(
        DEFAULT_DATABASE,
        "--database",
        envvar="CODEX_VECTOR_DB",
        help="Chroma database name",
    ),
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        envvar="CODEX_VECTOR_COLLECTION",
        help="Default collection for CLI commands",
    ),
) -> None:
    """Populate reusable configuration on the Typer context."""

    ctx.obj = AppConfig(
        base_url=base_url,
        tenant=tenant,
        database=database,
        collection=collection,
    )


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


class HashEmbeddings(Embeddings):
    """Deterministic fallback embeddings compatible with LangChain."""

    def __init__(self, dimension: int = DEFAULT_DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [generate_embedding(text, self.dimension) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return generate_embedding(text, self.dimension)


@lru_cache(maxsize=1)
def _embedding_function() -> Embeddings:
    model = os.environ.get("CODEX_EMBED_MODEL")
    provider = os.environ.get("CODEX_EMBED_PROVIDER", "auto").lower()
    dim = int(os.environ.get("CODEX_VECTOR_DIM", str(DEFAULT_DIM)))

    if provider in {"openai", "auto"} and OpenAIEmbeddings is not None:
        api_key = os.environ.get("OPENAI_API_KEY")
        target_model = model or os.environ.get("OPENAI_EMBED_MODEL")
        if api_key and target_model:
            try:
                return OpenAIEmbeddings(model=target_model)
            except Exception as exc:  # pragma: no cover - runtime guard
                typer.secho(f"OpenAI embeddings failed ({exc}); falling back", fg=typer.colors.YELLOW)
        elif api_key and provider == "openai":
            try:
                return OpenAIEmbeddings()
            except Exception as exc:  # pragma: no cover - runtime guard
                typer.secho(f"OpenAI embeddings failed ({exc}); falling back", fg=typer.colors.YELLOW)

    if provider in {"huggingface", "auto"} and HuggingFaceEmbeddings is not None:
        if model:
            try:
                return HuggingFaceEmbeddings(model_name=model)
            except Exception as exc:  # pragma: no cover - runtime guard
                typer.secho(f"HuggingFace embeddings failed ({exc}); falling back", fg=typer.colors.YELLOW)

    return HashEmbeddings(dim)


# ---------------------------------------------------------------------------
# Core client helpers
# ---------------------------------------------------------------------------


def _parse_base_url(base_url: str) -> Tuple[str, int, bool]:
    parsed = urlparse(base_url)
    if not parsed.scheme:
        parsed = urlparse(f"http://{base_url}")
    host = parsed.hostname or "127.0.0.1"
    if parsed.port:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    elif parsed.scheme == "http":
        port = 80
    else:
        port = 8000
    use_ssl = parsed.scheme == "https"
    return host, port, use_ssl


def _client(config: AppConfig) -> ClientAPI:
    host, port, use_ssl = _parse_base_url(config.base_url)
    return HttpClient(
        host=host,
        port=port,
        ssl=use_ssl,
        tenant=config.tenant,
        database=config.database,
    )


def _vectorstore(config: AppConfig, collection_name: str, create: bool = False) -> Chroma:
    client = _client(config)
    metadata = {"hnsw:space": "cosine"}
    if create:
        client.get_or_create_collection(collection_name, metadata=metadata)
    else:
        try:
            client.get_collection(collection_name)
        except NotFoundError as exc:
            raise typer.Exit(f"Collection '{collection_name}' not found") from exc
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=_embedding_function(),
        collection_metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _stable_doc_id(content: str, namespace: Optional[str] = None) -> str:
    hasher = hashlib.blake2b(digest_size=6)
    if namespace:
        hasher.update(namespace.encode("utf-8"))
    hasher.update(content.encode("utf-8"))
    return f"doc-{hasher.hexdigest()}"


def _load_documents(texts: List[str], file_path: Optional[Path]) -> List[str]:
    docs: List[str] = []
    docs.extend(text for text in texts if text)
    if file_path:
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                docs.extend(line.strip() for line in handle if line.strip())
        except OSError as exc:
            raise typer.Exit(f"Failed to read {file_path}: {exc}")
    return docs


def _flatten_metadatas(raw: Iterable) -> Iterable[Dict[str, object]]:
    for entry in raw:
        if isinstance(entry, dict):
            yield entry
        elif isinstance(entry, list):
            for sub in entry:
                if isinstance(sub, dict):
                    yield sub


def _iter_metadata(collection, batch_size: int = 500) -> Iterable[Dict[str, object]]:
    offset = 0
    total = collection.count()
    while offset < total:
        response = collection.get(include=["metadatas"], limit=batch_size, offset=offset)
        metadatas = response.get("metadatas") or []
        yielded = False
        for meta in _flatten_metadatas(metadatas):
            yielded = True
            yield meta
        if not yielded:
            break
        offset += batch_size


def _command_summary(collection, top: int) -> Dict[str, object]:
    metadata = list(_iter_metadata(collection))
    total_docs = collection.count()
    by_source = Counter((meta.get("source") or "(unknown)") for meta in metadata)
    by_doc_id = Counter((meta.get("doc_id") or "(missing)") for meta in metadata if meta.get("doc_id"))
    by_title = Counter((meta.get("title") or "(missing)") for meta in metadata if meta.get("title"))

    def _format(counter: Counter[str]) -> List[Dict[str, object]]:
        return [{"value": value, "count": count} for value, count in counter.most_common(top)]

    return {
        "collection": collection.name,
        "total_documents": total_docs,
        "top_sources": _format(by_source),
        "top_doc_ids": _format(by_doc_id),
        "top_titles": _format(by_title),
    }


def _print_summary(summary: Dict[str, object]) -> None:
    typer.echo(f"Collection: {summary['collection']}")
    typer.echo(f"Total documents: {summary['total_documents']}")

    def _section(title: str, items: List[Dict[str, object]]) -> None:
        typer.echo(f"\n{title}:")
        if not items:
            typer.echo("  (none)")
            return
        for entry in items:
            typer.echo(f"  - {entry['value']}: {entry['count']}")

    _section("Top sources", summary.get("top_sources", []))
    _section("Top doc IDs", summary.get("top_doc_ids", []))
    _section("Top titles", summary.get("top_titles", []))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def status(ctx: typer.Context) -> None:
    """Show connection metadata and available collections."""

    config: AppConfig = ctx.obj
    client = _client(config)

    host, port, use_ssl = _parse_base_url(config.base_url)
    proto = "https" if use_ssl else "http"
    typer.echo("Codex LangChain Vector CLI")
    typer.echo("============================")
    typer.echo(f"Base URL : {config.base_url}")
    typer.echo(f"Resolved : {proto}://{host}:{port}")
    typer.echo(f"Tenant   : {config.tenant}")
    typer.echo(f"Database : {config.database}")
    typer.echo(f"Default  : {config.collection}")
    typer.echo("")

    try:
        heartbeat = client.heartbeat()
        typer.echo(f"Heartbeat: {heartbeat}")
    except Exception as exc:  # pragma: no cover - runtime guard
        typer.secho(f"Heartbeat check failed: {exc}", fg=typer.colors.YELLOW)

    typer.echo("\nCollections:")
    collections = client.list_collections()
    if not collections:
        typer.echo("  (none)")
        return
    for coll in collections:
        try:
            count = coll.count()
        except Exception:  # pragma: no cover - API guard
            count = "?"
        typer.echo(f"  - {coll.name} :: docs={count}")


@app.command("list")
def list_collections(ctx: typer.Context) -> None:
    """List collections registered with Chroma."""

    config: AppConfig = ctx.obj
    client = _client(config)
    for coll in client.list_collections():
        typer.echo(coll.name)


@app.command()
def create(ctx: typer.Context, collection: str = typer.Argument(..., help="Collection name")) -> None:
    """Create a collection if it does not already exist."""

    config: AppConfig = ctx.obj
    client = _client(config)
    metadata = {"hnsw:space": "cosine"}
    coll = client.get_or_create_collection(collection, metadata=metadata)
    typer.echo(f"Collection '{coll.name}' is ready")


@app.command()
def query(
    ctx: typer.Context,
    query_text: str = typer.Argument(..., help="Free form query text"),
    collection: str = typer.Option(None, "--collection", help="Collection to query"),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum number of results"),
) -> None:
    """Run a similarity search using LangChain and print scored results."""

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    vectorstore = _vectorstore(config, target_collection)

    results = vectorstore.similarity_search_with_score(query_text, k=limit)
    typer.echo(f"Query results for '{query_text}':")
    if not results:
        typer.echo("  (no matches)")
        return

    for doc, score in results:
        distance = f"{score:.4f}" if isinstance(score, (float, int)) else str(score)
        typer.echo(f"  - distance={distance} :: {doc.page_content}")
        if doc.metadata:
            typer.echo(f"      metadata={doc.metadata}")


@app.command()
def search(
    ctx: typer.Context,
    query_text: str = typer.Argument(..., help="Free form query text"),
    collection: str = typer.Option(None, "--collection", help="Collection to query"),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum number of results"),
) -> None:
    """Alias for ``query``."""

    ctx.invoke(query, ctx=ctx, query_text=query_text, collection=collection, limit=limit)


@app.command()
def add(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="Document text to store"),
    collection: str = typer.Option(None, "--collection", help="Target collection"),
    source: Optional[str] = typer.Option(None, "--source", help="Optional metadata source"),
) -> None:
    """Add a single document to a collection."""

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    vectorstore = _vectorstore(config, target_collection, create=True)

    metadata = {"source": source or DEFAULT_TAG}
    doc_id = _stable_doc_id(content, source)
    vectorstore.add_texts([content], metadatas=[{**metadata, "doc_id": doc_id}], ids=[doc_id])
    typer.echo(f"Stored document in '{target_collection}' with id={doc_id}")


@app.command()
def upsert(
    ctx: typer.Context,
    collection: str = typer.Option(None, "--collection", help="Target collection"),
    text: List[str] = typer.Option(
        [],
        "--text",
        help="Inline document text (repeatable)",
        rich_help_panel="Content",
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Path to UTF-8 text file; each non-empty line becomes a document",
        rich_help_panel="Content",
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        help="Optional metadata source tag",
    ),
    create: bool = typer.Option(
        False,
        "--create",
        help="Create the collection automatically if it does not exist",
    ),
) -> None:
    """Upsert one or more documents into the target collection."""

    docs = _load_documents(text, file)
    if not docs:
        raise typer.Exit("No documents provided")

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    vectorstore = _vectorstore(config, target_collection, create=create)

    metadatas: List[Dict[str, object]] = []
    ids: List[str] = []
    for idx, doc in enumerate(docs):
        source_tag = tag or (file.name if file else DEFAULT_TAG)
        metadata = {"source": source_tag, "position": idx}
        doc_id = _stable_doc_id(doc, f"{source_tag}:{idx}")
        metadata["doc_id"] = doc_id
        metadatas.append(metadata)
        ids.append(doc_id)

    vectorstore.add_texts(docs, metadatas=metadatas, ids=ids)
    typer.echo(f"Upserted {len(docs)} document(s) into '{target_collection}'")


@app.command()
def stats(
    ctx: typer.Context,
    collection: str = typer.Option(None, "--collection", help="Collection to inspect"),
    top: int = typer.Option(5, "--top", min=1, max=50, help="Top metadata values to display"),
    json_output: Optional[Path] = typer.Option(
        None,
        "--json",
        path_type=Path,
        help="Optional path to write JSON summary",
    ),
) -> None:
    """Display collection statistics and optional JSON summary."""

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    client = _client(config)
    try:
        chroma_collection = client.get_collection(target_collection)
    except NotFoundError as exc:
        raise typer.Exit(f"Collection '{target_collection}' not found") from exc

    summary = _command_summary(chroma_collection, top=top)
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        typer.echo(f"Stats written to {json_output}")
    else:
        _print_summary(summary)


@app.command()
def setup(
    ctx: typer.Context,
    collection: str = typer.Option(None, "--collection", help="Collection to seed"),
) -> None:
    """Seed the default setup snippets using LangChain upserts."""

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    vectorstore = _vectorstore(config, target_collection, create=True)

    docs: List[str] = []
    metadatas: List[Dict[str, object]] = []
    for idx, (command, description, examples) in enumerate(DEFAULT_SETUP_SNIPPETS):
        block = [f"Command: {command}", f"Description: {description}"]
        if examples:
            block.append("Examples: " + "; ".join(examples))
        payload = "\n".join(block)
        doc_id = _stable_doc_id(payload, f"setup:{command}")
        docs.append(payload)
        metadatas.append({"source": "setup", "doc_id": doc_id, "position": idx})

    vectorstore.add_texts(docs, metadatas=metadatas, ids=[meta["doc_id"] for meta in metadatas])
    typer.echo(f"Seeded {len(docs)} command snippets into '{target_collection}'")


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
