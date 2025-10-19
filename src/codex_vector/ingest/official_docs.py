#!/usr/bin/env python3
"""Fetch official Codex documentation and load it into the vector database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

import requests

from ..client import CodexVectorClient

RAW_BASE = "https://raw.githubusercontent.com/openai/openai-cookbook/main"

DOC_SPECS: List[Dict[str, str]] = [
    {
        "id": "openai-cookbook-codex-secure-gitlab",
        "title": "Secure Quality Reviews with GitLab",
        "url": f"{RAW_BASE}/examples/codex/secure_quality_gitlab.md",
        "format": "markdown",
    },
    {
        "id": "openai-cookbook-codex-jira-github",
        "title": "Jira GitHub Automation",
        "url": f"{RAW_BASE}/examples/codex/jira-github.ipynb",
        "format": "ipynb",
    },
    {
        "id": "openai-cookbook-codex-autofix-actions",
        "title": "Autofix GitHub Actions",
        "url": f"{RAW_BASE}/examples/codex/Autofix-github-actions.ipynb",
        "format": "ipynb",
    },
    {
        "id": "openai-cookbook-codex-prompting-guide",
        "title": "GPT-5 Codex Prompting Guide",
        "url": f"{RAW_BASE}/examples/gpt-5-codex_prompting_guide.ipynb",
        "format": "ipynb",
    },
]


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 150) -> Iterable[str]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chars, length)
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


def fetch_content(spec: Dict[str, str]) -> str:
    url = spec["url"]
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    if spec["format"] == "markdown":
        return resp.text
    if spec["format"] == "ipynb":
        data = json.loads(resp.text)
        parts: List[str] = []
        for cell in data.get("cells", []):
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue
            if cell.get("cell_type") == "markdown":
                parts.append(source)
            elif cell.get("cell_type") == "code":
                parts.append("```python\n" + source + "\n```")
        return "\n\n".join(parts)
    raise ValueError(f"Unsupported format: {spec['format']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch official Codex documentation")
    parser.add_argument(
        "--collection", default="codex_agent", help="Target collection name"
    )
    parser.add_argument("--max-chars", type=int, default=900, help="Chunk size")
    parser.add_argument("--overlap", type=int, default=150, help="Chunk overlap")
    parser.add_argument(
        "--batch-size", type=int, default=16, help="Batch size for upserts"
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/codex/official_docs"),
        help="Directory to store fetched text",
    )
    args = parser.parse_args()

    dest_dir: Path = args.dest
    dest_dir.mkdir(parents=True, exist_ok=True)

    cli = CodexVectorClient()
    all_chunks: List[Dict[str, str]] = []

    for spec in DOC_SPECS:
        try:
            content = fetch_content(spec)
        except Exception as exc:
            print(f"⚠️  Failed to fetch {spec['url']}: {exc}")
            continue

        text_path = dest_dir / f"{spec['id']}.txt"
        text_path.write_text(content, encoding="utf-8")

        for index, chunk in enumerate(
            chunk_text(content, max_chars=args.max_chars, overlap=args.overlap), start=1
        ):
            all_chunks.append(
                {
                    "text": chunk,
                    "metadata": {
                        "source": spec["url"],
                        "doc_id": spec["id"],
                        "title": spec["title"],
                        "chunk": index,
                    },
                }
            )

    if not all_chunks:
        print("No documents fetched; nothing to ingest.")
        return 0

    for start in range(0, len(all_chunks), args.batch_size):
        batch = all_chunks[start : start + args.batch_size]
        cli.upsert(
            args.collection,
            [item["text"] for item in batch],
            metadata_items=[item["metadata"] for item in batch],
            create_collection=True,
        )

    print(
        f"Ingested {len(all_chunks)} chunks from official sources into '{args.collection}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
