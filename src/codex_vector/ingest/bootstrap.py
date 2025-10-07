#!/usr/bin/env python3
"""Bootstrap the Codex vector database with project documentation.

This script collects content from key project files, chunks it, and loads the
snippets into the configured Chroma collection. It relies on the core CLI
implementation so embeddings and collection handling stay consistent.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

from ..client import CodexVectorClient

DEFAULT_FILES = [
    Path("README.md"),
    Path("docs/codex_integration_guide.md"),
    Path("docs/vector_db_research.md"),
]


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 150) -> Iterable[str]:
    """Yield sliding-window chunks while preserving sentence boundaries when possible."""

    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chars, length)
        # Try to end on a paragraph boundary for readability
        boundary = cleaned.rfind("\n\n", start, end)
        if boundary != -1 and boundary > start + 100:
            end = boundary
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def collect_documents(paths: List[Path], *, max_chars: int, overlap: int) -> List[dict]:
    documents: List[dict] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, chunk in enumerate(chunk_text(text, max_chars=max_chars, overlap=overlap), start=1):
            documents.append(
                {
                    "text": chunk,
                    "metadata": {
                        "source": str(path),
                        "chunk": index,
                        "total_chars": len(chunk),
                    },
                }
            )
    return documents


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Codex vector database with project docs")
    parser.add_argument("--collection", default="codex_agent", help="Collection name to populate")
    parser.add_argument("--max-chars", type=int, default=900, help="Chunk size for document splitting")
    parser.add_argument("--overlap", type=int, default=150, help="Character overlap between chunks")
    parser.add_argument(
        "--paths",
        nargs="*",
        type=Path,
        default=DEFAULT_FILES,
        help="Files to ingest (defaults to key project docs)",
    )
    parser.add_argument("--batch-size", type=int, default=16, help="Number of chunks to upsert per request")
    args = parser.parse_args()

    cli = CodexVectorClient()
    docs = collect_documents(list(args.paths), max_chars=args.max_chars, overlap=args.overlap)
    if not docs:
        print("No documents found to ingest.")
        return 0

    for batch_start in range(0, len(docs), args.batch_size):
        batch = docs[batch_start : batch_start + args.batch_size]
        texts = [entry["text"] for entry in batch]
        metadata = [entry["metadata"] for entry in batch]
        cli.upsert(
            args.collection,
            texts,
            metadata_items=metadata,
            create_collection=True,
        )

    print(f"Ingested {len(docs)} chunks into collection '{args.collection}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
