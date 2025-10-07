#!/usr/bin/env python3
"""Typer CLI for interacting with the Meilisearch keyword index."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import typer

if __package__ is None or __package__ == "":  # pragma: no cover - script entry
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_keyword.client import KeywordSearchClient
else:
    from .client import KeywordSearchClient

app = typer.Typer(help="Keyword search utilities backed by Meilisearch")

DEFAULT_INDEX = os.environ.get("CODEX_MEILI_INDEX", "codex_os_search")
DEFAULT_INCLUDE = {".md", ".txt", ".log", ".conf", ".ini", ".yaml", ".yml", ".py", ".sh", ".service", ".json"}
DEFAULT_EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "vendor", "build", "dist"}


def _iter_files(paths: Iterable[Path], *, include: set[str], exclude_dirs: set[str], max_bytes: int) -> Iterable[Path]:
    for base in paths:
        if not base.exists():
            continue
        if base.is_file():
            if include and base.suffix and base.suffix.lower() not in include:
                continue
            yield base
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                if path.name in exclude_dirs:
                    # skip entire subtree
                    dirs_to_skip = [p for p in path.iterdir()]  # exhaust to avoid recursion
                    continue
                continue
            if include and path.suffix and path.suffix.lower() not in include:
                continue
            if path.stat().st_size > max_bytes:
                continue
            yield path


def _read_file(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="latin-1")
        except Exception:
            return None
    except Exception:
        return None
    return text.strip() or None


@app.command()
def status(
    index: str = typer.Option(DEFAULT_INDEX, "--index", help="Index name to inspect"),
) -> None:
    """Display Meilisearch health, version, and index metadata."""

    client = KeywordSearchClient(index_name=index)
    typer.echo("Meilisearch status")
    typer.echo("==================")
    typer.echo(json.dumps({
        "health": client.health(),
        "version": client.version(),
        "indexes": client.list_indexes(),
    }, indent=2))


@app.command()
def create(
    index: str = typer.Option(DEFAULT_INDEX, "--index", help="Index to create"),
    primary_key: str = typer.Option("id", "--primary-key", help="Primary key field"),
) -> None:
    """Create the target index if it does not exist."""

    client = KeywordSearchClient(index_name=index)
    info = client.ensure_index(index=index, primary_key=primary_key)
    typer.echo(f"Index '{index}' ready (primary key: {primary_key})")
    typer.echo(json.dumps(info, indent=2))


@app.command()
def drop(
    index: str = typer.Option(DEFAULT_INDEX, "--index", help="Index to remove"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Delete an index and its documents."""

    if not yes and not typer.confirm(f"Delete index '{index}'?"):
        raise typer.Exit(code=1)
    client = KeywordSearchClient(index_name=index)
    client.delete_index(index)
    typer.echo(f"Index '{index}' deleted (if it existed).")


@app.command()
def index_path(
    paths: List[Path] = typer.Argument(..., exists=True, help="Files or directories to index"),
    index: str = typer.Option(DEFAULT_INDEX, "--index", help="Target index"),
    include: List[str] = typer.Option(list(DEFAULT_INCLUDE), "--include", help="File extensions to include"),
    exclude_dir: List[str] = typer.Option(list(DEFAULT_EXCLUDE_DIRS), "--exclude-dir", help="Directory names to ignore"),
    max_bytes: int = typer.Option(4_000_000, "--max-bytes", help="Skip files larger than this many bytes"),
    batch_size: int = typer.Option(500, "--batch-size", help="Documents to send per batch"),
    source_prefix: Optional[str] = typer.Option(None, "--source-prefix", help="Prefix stored with each source path"),
) -> None:
    """Index the given files/directories into Meilisearch."""

    client = KeywordSearchClient(index_name=index)
    client.ensure_index(index=index, primary_key="id")

    include_set = {suffix.lower() if suffix.startswith('.') else f'.{suffix.lower()}' for suffix in include}
    exclude_dirs = set(exclude_dir)

    documents = []
    total = 0
    for path in _iter_files(paths, include=include_set, exclude_dirs=exclude_dirs, max_bytes=max_bytes):
        content = _read_file(path)
        if not content:
            continue
        rel = path.resolve().as_posix()
        source = f"{source_prefix}{rel}" if source_prefix else rel
        doc = {
            "id": rel,
            "path": rel,
            "name": path.name,
            "content": content,
            "source": source,
        }
        documents.append(doc)
        total += 1

    if not documents:
        typer.echo("No documents to index")
        raise typer.Exit()

    response = client.add_documents(documents, index=index, batch_size=batch_size)
    typer.echo(json.dumps({"indexed": total, "response": response}, indent=2))


@app.command()
def search(
    query: str = typer.Argument(..., help="Query string"),
    index: str = typer.Option(DEFAULT_INDEX, "--index", help="Index to search"),
    limit: int = typer.Option(10, "--limit", help="Maximum hits to return"),
    json_output: Optional[Path] = typer.Option(None, "--json", help="Optional output path for raw JSON"),
) -> None:
    """Run a keyword search and display the top hits."""

    client = KeywordSearchClient(index_name=index)
    result = client.search(query, index=index, limit=limit)
    hits = result.get("hits", [])
    typer.echo(f"Search results for '{query}' (index={index})")
    typer.echo("==========================================")
    if not hits:
        typer.echo("(no matches)")
    else:
        for hit in hits:
            path = hit.get("path") or hit.get("id")
            snippet = hit.get("content", "").replace("\n", " ")[:180]
            typer.echo(f"- {path}\n    {snippet}")
    if json_output:
        json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        typer.echo(f"Raw response written to {json_output}")


def main() -> None:  # pragma: no cover
    try:
        app()
    except KeyboardInterrupt:
        raise typer.Exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
