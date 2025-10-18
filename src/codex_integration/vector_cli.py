#!/usr/bin/env python3
"""LangChain-integrated vector CLI for Codex agents.

The CLI now targets both Mindstack Core (Chroma) and the production-grade
Qdrant backend through the unified ``CodexVectorClient`` abstraction. Commands
preserve the existing UX while gaining incremental upserts and backend auto-
selection.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import typer

SRC_ROOT = Path(__file__).resolve().parent.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

PROJECT_ROOT = SRC_ROOT.parent


def _load_workspace_env() -> None:
    """Load .env variables so CLI defaults match Mindstack runtime."""

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
    except OSError:
        # Silently ignore unreadable .env to avoid breaking the CLI.
        return


_load_workspace_env()

from codex_vector.client import (  # noqa: E402  # pylint: disable=wrong-import-position
    CodexVectorClient,
    DEFAULT_BASE_URL,
    DEFAULT_DATABASE,
    DEFAULT_TENANT,
)
from codex_vector.constants import DEFAULT_SETUP_SNIPPETS  # noqa: E402  # pylint: disable=wrong-import-position

app = typer.Typer(help="Mindstack vector CLI for Codex agents (Chroma & Qdrant)")

DEFAULT_COLLECTION = os.environ.get("CODEX_VECTOR_COLLECTION", "codex_agent")
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
        help="Mindstack vector base URL (auto-detects Chroma vs. Qdrant)",
    ),
    tenant: str = typer.Option(
        DEFAULT_TENANT,
        "--tenant",
        envvar="CODEX_VECTOR_TENANT",
        help="Tenant identifier (Chroma only)",
    ),
    database: str = typer.Option(
        DEFAULT_DATABASE,
        "--database",
        envvar="CODEX_VECTOR_DB",
        help="Database name (Chroma only)",
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
# Utility helpers
# ---------------------------------------------------------------------------


def _client_from_ctx(config: AppConfig) -> CodexVectorClient:
    return CodexVectorClient(
        base_url=config.base_url,
        tenant=config.tenant,
        database=config.database,
    )


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


def _command_summary(
    collection: str,
    total_documents: int,
    metadata: Iterable[Dict[str, object]],
    top: int,
) -> Dict[str, object]:
    by_source = Counter()
    by_doc_id = Counter()
    by_title = Counter()

    for entry in metadata:
        source = entry.get("source") or "(unknown)"
        by_source[source] += 1
        doc_id = entry.get("doc_id") or "(missing)"
        by_doc_id[doc_id] += 1
        title = entry.get("title") or "(missing)"
        by_title[title] += 1

    def _format(counter: Counter[str]) -> List[Dict[str, object]]:
        return [{"value": value, "count": count} for value, count in counter.most_common(top)]

    return {
        "collection": collection,
        "total_documents": total_documents,
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
    """Show backend information and available collections."""

    config: AppConfig = ctx.obj
    client = _client_from_ctx(config)
    client.status()


@app.command()
def query(
    ctx: typer.Context,
    query_text: str = typer.Argument(..., help="Free form query text"),
    collection: str = typer.Option(None, "--collection", help="Collection to query"),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum number of results"),
) -> None:
    """Run a similarity search against a collection."""

    config: AppConfig = ctx.obj
    target_collection = collection or config.collection
    client = _client_from_ctx(config)
    client.query(target_collection, query_text, limit=limit)


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
    client = _client_from_ctx(config)
    target_collection = collection or config.collection
    tag = source or DEFAULT_TAG
    client.upsert(
        target_collection,
        [content],
        metadata_source=tag,
        create_collection=True,
    )


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
    client = _client_from_ctx(config)
    target_collection = collection or config.collection
    client.upsert(
        target_collection,
        docs,
        metadata_source=tag or (file.name if file else DEFAULT_TAG),
        create_collection=create,
    )


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
    client = _client_from_ctx(config)
    target_collection = collection or config.collection

    try:
        total_docs = client.collection_count(target_collection)
    except RuntimeError as exc:
        raise typer.Exit(str(exc))

    metadata = list(client.iter_metadata(target_collection))
    summary = _command_summary(target_collection, total_docs, metadata, top=top)

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
    """Seed the default setup snippets using backend-aware upserts."""

    config: AppConfig = ctx.obj
    client = _client_from_ctx(config)
    target_collection = collection or config.collection

    docs: List[str] = []
    metadatas: List[Dict[str, object]] = []
    for idx, (command, description, examples) in enumerate(DEFAULT_SETUP_SNIPPETS):
        block = [f"Command: {command}", f"Description: {description}"]
        if examples:
            block.append("Examples: " + "; ".join(examples))
        payload = "\n".join(block)
        docs.append(payload)
        metadatas.append({"source": "setup", "position": idx, "command": command})

    client.upsert(
        target_collection,
        docs,
        metadata_items=metadatas,
        create_collection=True,
    )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
