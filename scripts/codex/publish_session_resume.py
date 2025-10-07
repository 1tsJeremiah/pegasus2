#!/usr/bin/env python3
"""Generate a markdown session resume and ingest it into the vector database."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

from codex_vector.client import CodexVectorClient


def _normalize_items(items: List[str]) -> List[str]:
    normalized: List[str] = []
    for raw in items:
        text = raw.strip()
        if not text:
            continue
        if not text.startswith("- ") and not text.startswith("-\t") and not text.startswith("-\n") and not text.startswith("-"):
            text = f"- {text}"
        normalized.append(text)
    return normalized


def _load_items(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Summary file not found: {path}")
    return [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_document(session_id: str, snapshot: List[str], follow_up: List[str], *, label: str | None) -> str:
    display = label or session_id.split("-")[0] or session_id
    sections: List[str] = [
        f"# Session Resume - {display}",
        "",
        "## Thread Snapshot",
        "\n".join(snapshot) if snapshot else "(empty)",
    ]
    if follow_up:
        sections.extend([
            "",
            "## Follow-up Hooks",
            "\n".join(follow_up),
        ])
    sections.append("")
    return "\n".join(sections)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create and publish a Codex session resume")
    parser.add_argument("session_id", help="Full Codex session identifier (UUID)")
    parser.add_argument("--label", help="Optional short label used in the markdown title")
    parser.add_argument(
        "--snapshot",
        action="append",
        dest="snapshot_items",
        default=[],
        help="Bullet item for the thread snapshot section (repeatable)",
    )
    parser.add_argument(
        "--snapshot-file",
        type=Path,
        help="Load snapshot bullet items from a file (one item per line)",
    )
    parser.add_argument(
        "--follow",
        action="append",
        dest="follow_items",
        default=[],
        help="Bullet item for the follow-up section (repeatable)",
    )
    parser.add_argument(
        "--follow-file",
        type=Path,
        help="Load follow-up bullet items from a file (one item per line)",
    )
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=Path.home() / "Documents" / "codex-resumes",
        help="Destination directory for human-readable resumes",
    )
    parser.add_argument(
        "--collection",
        default="session-resumes",
        help="Vector collection used for agent access",
    )
    parser.add_argument("--base-url", default=None, help="Override Codex vector base URL")
    parser.add_argument("--tenant", default=None, help="Override Codex vector tenant name")
    parser.add_argument("--database", default=None, help="Override Codex vector database name")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the markdown but skip vector ingestion",
    )

    args = parser.parse_args(argv)

    snapshot_items: List[str] = []
    if args.snapshot_file:
        snapshot_items.extend(_load_items(args.snapshot_file))
    if args.snapshot_items:
        snapshot_items.extend(args.snapshot_items)

    follow_items: List[str] = []
    if args.follow_file:
        follow_items.extend(_load_items(args.follow_file))
    if args.follow_items:
        follow_items.extend(args.follow_items)

    if not snapshot_items:
        parser.error("At least one snapshot item is required")

    snapshot = _normalize_items(snapshot_items)
    follow_up = _normalize_items(follow_items)

    markdown = build_document(args.session_id, snapshot, follow_up, label=args.label)

    documents_dir: Path = args.documents_dir.expanduser()
    documents_dir.mkdir(parents=True, exist_ok=True)
    label = args.label or args.session_id.split("-")[0]
    output_path = documents_dir / f"session-{label}.md"
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Resume written to {output_path}")

    if args.dry_run:
        return 0

    defaults = CodexVectorClient()
    base_url = args.base_url or os.environ.get("CODEX_VECTOR_BASE_URL") or defaults.base_url
    tenant = args.tenant or os.environ.get("CODEX_VECTOR_TENANT") or defaults.tenant
    database = args.database or os.environ.get("CODEX_VECTOR_DB") or defaults.database

    cli = CodexVectorClient(base_url=base_url, tenant=tenant, database=database)

    metadata = {
        "source": f"resume/{label}",
        "session_id": args.session_id,
        "title": f"Session {label} resume",
        "human_doc": str(output_path),
    }

    cli.upsert(
        args.collection,
        [markdown],
        metadata_items=[metadata],
        create_collection=True,
    )
    print(f"Ingested resume into collection '{args.collection}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
