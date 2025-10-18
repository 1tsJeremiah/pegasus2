#!/usr/bin/env python3
"""Ingest non-audio Desktop artifacts into Mindstack."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Iterable, List

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from codex_vector.client import CodexVectorClient

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg"}
TEXT_EXTS = {
    ".txt",
    ".log",
    ".pem",
    ".crt",
    ".conf",
    ".cfg",
    ".ini",
    ".json",
    ".xml",
    ".md",
}
CHUNK_SIZE = 1800
INGEST_TAG = "desktop-ingest-2025-10-16"
COLLECTION = "codex_agent"

root = Path.home() / "Desktop"
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            val = value.strip().strip('"').strip("'")
            os.environ[key] = val

os.environ["CODEX_QDRANT_USE_GRPC"] = "1"
os.environ["CODEX_QDRANT_GRPC_PORT"] = "6334"
os.environ["CODEX_VECTOR_BASE_URL"] = "http://127.0.0.1:6333"
os.environ["CODEX_VECTOR_BACKEND"] = "qdrant"

client = CodexVectorClient()
try:
    client.ensure_collection(COLLECTION)
except Exception:
    try:
        client.create_collection(COLLECTION)
    except Exception:
        pass


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    text = text.strip()
    if not text:
        return []
    segments: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        segments.append(text[start:end])
        start = end
    return segments


def run_file_command(path: Path) -> str:
    result = subprocess.run(["file", "-b", str(path)], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.stdout else "(file command produced no output)"


def ingest_segments(segments: Iterable[str], *, source_path: Path, note: str) -> None:
    segments = [seg for seg in segments if seg.strip()]
    if not segments:
        return
    metadata = []
    rel_path = source_path.as_posix()
    for idx, _ in enumerate(segments):
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{rel_path}:{note}:{idx}"))
        metadata.append(
            {
                "source_path": rel_path,
                "chunk_index": idx,
                "ingest_tag": INGEST_TAG,
                "note": note,
                "doc_id": doc_uuid,
            }
        )
    client.upsert(COLLECTION, segments, metadata_items=metadata)


def ingest_text_file(path: Path, *, note: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    header = f"Filename: {path.as_posix()}\nNote: {note}\n\n"
    segments = chunk_text(header + text)
    ingest_segments(segments, source_path=path, note=note)


def ingest_sqlog(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="ignore")
    summary = (
        f"Filename: {path.as_posix()}\n"
        f"Type: QUIC qlog JSON sequence exported from Cloudflare WARP client.\n"
        f"First 10 lines:\n{chr(10).join(content.splitlines()[:10])}\n\n"
    )
    segments = chunk_text(summary + content)
    ingest_segments(segments, source_path=path, note="cloudflare-quic-qlog")


def ingest_image_summary(path: Path) -> None:
    info = run_file_command(path)
    size = path.stat().st_size
    summary = (
        f"Filename: {path.as_posix()}\n"
        f"Type: PNG image screenshot stored in Desktop.\n"
        f"file(1) report: {info}\n"
        f"Filesize: {size} bytes\n"
        f"Description: Visual asset retained for reference. Use external viewer to inspect." 
    )
    segments = chunk_text(summary)
    ingest_segments(segments, source_path=path, note="image-metadata")


def ingest_zip_summary(path: Path) -> None:
    listing = subprocess.run(
        ["unzip", "-l", str(path)], capture_output=True, text=True, check=False
    ).stdout
    summary = (
        f"Filename: {path.as_posix()}\n"
        f"Type: ZIP archive (Android Lawnchair backup).\n"
        f"Contents via `unzip -l`:\n{listing.strip()}\n"
        f"Description: Use extracted files in Desktop/shed_extract for detailed data."
    )
    segments = chunk_text(summary)
    ingest_segments(segments, source_path=path, note="zip-summary")


def ingest_sqlite_summary(path: Path) -> None:
    lines = []
    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        lines.append(f"Tables: {', '.join(tables) if tables else 'none'}")
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                lines.append(f"Rows in {table}: {count}")
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                lines.append(f"Failed counting rows in {table}: {exc}")
    summary = (
        f"Filename: {path.as_posix()}\n"
        f"Type: SQLite database extracted from Lawnchair backup.\n"
        + "\n".join(lines)
    )
    segments = chunk_text(summary)
    ingest_segments(segments, source_path=path, note="sqlite-summary")


def main() -> None:
    targets = sorted(root.iterdir())
    for path in targets:
        if path.is_dir():
            # Ingest shed_extract contents but skip audio directories.
            if path.name == "shed_extract":
                for subpath in sorted(path.iterdir()):
                    if subpath.suffix.lower() in AUDIO_EXTS:
                        continue
                    if subpath.suffix.lower() in TEXT_EXTS or subpath.name.endswith(".xml") or subpath.name == "lcbkp":
                        ingest_text_file(subpath, note="shed-extract")
                    elif subpath.suffix.lower() == ".db":
                        ingest_sqlite_summary(subpath)
                    elif subpath.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                        ingest_image_summary(subpath)
                continue
            # Other directories are ignored for now
            continue

        suffix = path.suffix.lower()
        if suffix in AUDIO_EXTS:
            continue
        if suffix == ".pdf":
            # Corresponding .txt already generated
            continue
        if suffix in TEXT_EXTS or path.name.endswith(".txt"):
            ingest_text_file(path, note="desktop-text")
        elif suffix == ".sqlog":
            ingest_sqlog(path)
        elif suffix in {".png", ".jpg", ".jpeg"}:
            ingest_image_summary(path)
        elif suffix == ".shed":
            ingest_zip_summary(path)
        elif suffix == ".db":
            ingest_sqlite_summary(path)
        else:
            summary = (
                f"Filename: {path.as_posix()}\n"
                f"Type: {run_file_command(path)}\n"
                "Summary: Binary artifact captured on Desktop and retained for manual review." 
            )
            ingest_segments(chunk_text(summary), source_path=path, note="desktop-binary-summary")


if __name__ == "__main__":
    main()
