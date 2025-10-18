#!/usr/bin/env python3
"""Download and ingest key Ubuntu documentation PDFs into the vector database."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

import requests
from pypdf import PdfReader

from ..client import CodexVectorClient

try:  # Playwright is required for Cloudflare-protected assets
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional dependency in some environments
    sync_playwright = None


@dataclass
class DocSpec:
    doc_id: str
    title: str
    download_url: str
    filename: str
    category: str
    page_url: Optional[str] = None
    requires_playwright: bool = False


DOC_SPECS: List[DocSpec] = [
    DocSpec(
        doc_id="ubuntu-server-guide-2024-01-22",
        title="Ubuntu Server Guide (2024-01-22)",
        download_url="https://help.ubuntu.com/lts/serverguide/serverguide.pdf",
        filename="ubuntu-server-guide-2024-01-22.pdf",
        category="server-guide",
    ),
    DocSpec(
        doc_id="lubuntu-manual-24-04",
        title="Lubuntu 24.04 Manual",
        download_url="https://people.ubuntu.com/~guiverc/lubuntu_24.04_manual.pdf",
        filename="lubuntu_24.04_manual.pdf",
        category="desktop-manual",
    ),
    DocSpec(
        doc_id="ubuntu-desktop-user-guide",
        title="Ubuntu Desktop User Guide",
        download_url="https://people.ubuntu.com/~lyz/ubuntu-docs/ubuntu-user-guide.pdf",
        filename="ubuntu-user-guide.pdf",
        category="desktop-guide",
    ),
    DocSpec(
        doc_id="ubuntu-pro",
        title="Ubuntu Pro Guide",
        download_url="https://documentation.ubuntu.com/_/downloads/pro/en/latest/pdf/",
        filename="ubuntu-pro.pdf",
        category="ubuntu-pro",
        page_url="https://documentation.ubuntu.com/pro/en/latest/",
        requires_playwright=True,
    ),
    DocSpec(
        doc_id="ubuntu-on-aws",
        title="Ubuntu on AWS Guide",
        download_url="https://documentation.ubuntu.com/_/downloads/aws/en/latest/pdf/",
        filename="ubuntu-on-aws.pdf",
        category="cloud-aws",
        page_url="https://documentation.ubuntu.com/aws/en/latest/",
        requires_playwright=True,
    ),
    DocSpec(
        doc_id="ubuntu-on-gcp",
        title="Ubuntu on GCP Guide",
        download_url="https://documentation.ubuntu.com/_/downloads/gcp/en/latest/pdf/",
        filename="ubuntu-on-gcp.pdf",
        category="cloud-gcp",
        page_url="https://documentation.ubuntu.com/gcp/en/latest/",
        requires_playwright=True,
    ),
]


def fetch_with_requests(url: str, dest: Path) -> None:
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with dest.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handle.write(chunk)


def fetch_with_playwright(specs: List[DocSpec], dest_dir: Path) -> None:
    if not specs:
        return
    if sync_playwright is None:
        raise RuntimeError(
            "playwright is not installed; run `pip install playwright && playwright install chromium`."
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        for spec in specs:
            target = dest_dir / spec.filename
            if target.exists():
                continue
            page.goto(spec.page_url, wait_until="networkidle")  # type: ignore[arg-type]
            response = context.request.get(spec.download_url)
            if not response.ok:
                raise RuntimeError(
                    f"Failed to download {spec.title}: HTTP {response.status}"
                )
            target.write_bytes(response.body())
        browser.close()


def download_documents(
    specs: List[DocSpec], dest_dir: Path, force: bool = False
) -> List[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []

    playwright_specs = [spec for spec in specs if spec.requires_playwright]
    direct_specs = [spec for spec in specs if not spec.requires_playwright]

    for spec in direct_specs:
        target = dest_dir / spec.filename
        if force or not target.exists():
            fetch_with_requests(spec.download_url, target)
        downloaded.append(target)

    pending_playwright = []
    for spec in playwright_specs:
        target = dest_dir / spec.filename
        if force or not target.exists():
            pending_playwright.append(spec)
        else:
            downloaded.append(target)

    if pending_playwright:
        fetch_with_playwright(pending_playwright, dest_dir)
        downloaded.extend(dest_dir / spec.filename for spec in pending_playwright)

    return downloaded


def extract_paragraphs(pdf_path: Path) -> Iterator[tuple[str, int]]:
    reader = PdfReader(str(pdf_path))
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""
        raw_text = raw_text.replace("\r", "\n")
        raw_text = re.sub(r"\f", "\n", raw_text)
        raw_text = raw_text.replace("\u2022", "- ")
        for block in re.split(r"\n\s*\n", raw_text):
            normalized = " ".join(block.split())
            if normalized:
                yield normalized, page_number


def chunk_paragraphs(
    paragraphs: Iterable[tuple[str, int]],
    *,
    chunk_size: int,
    overlap: int,
) -> Iterator[tuple[str, int, int]]:
    buffer: List[tuple[str, int]] = []
    length = 0

    for text, page in paragraphs:
        if buffer and length + len(text) > chunk_size:
            combined = "\n\n".join(item[0] for item in buffer)
            start_page = buffer[0][1]
            end_page = buffer[-1][1]
            yield combined, start_page, end_page

            overlap_buffer: List[tuple[str, int]] = []
            overlap_len = 0
            for item in reversed(buffer):
                overlap_buffer.insert(0, item)
                overlap_len += len(item[0])
                if overlap_len >= overlap:
                    break
            buffer = overlap_buffer
            length = sum(len(item[0]) for item in buffer)

        buffer.append((text, page))
        length += len(text)

    if buffer:
        combined = "\n\n".join(item[0] for item in buffer)
        start_page = buffer[0][1]
        end_page = buffer[-1][1]
        yield combined, start_page, end_page


def ingest_pdfs(
    specs: List[DocSpec],
    downloaded: List[Path],
    *,
    collection: str,
    chunk_size: int,
    overlap: int,
) -> None:
    cli = CodexVectorClient()
    cli.ensure_collection(collection)

    spec_by_filename = {spec.filename: spec for spec in specs}

    for pdf_path in downloaded:
        spec = spec_by_filename.get(pdf_path.name)
        if spec is None:
            continue
        documents: List[str] = []
        metadatas: List[dict] = []
        for index, (text, start_page, end_page) in enumerate(
            chunk_paragraphs(
                extract_paragraphs(pdf_path), chunk_size=chunk_size, overlap=overlap
            ),
            start=1,
        ):
            documents.append(text)
            metadatas.append(
                {
                    "source": spec.download_url,
                    "title": spec.title,
                    "category": spec.category,
                    "doc_id": spec.doc_id,
                    "chunk_index": index,
                    "page_start": start_page,
                    "page_end": end_page,
                    "file_path": str(pdf_path),
                }
            )

        if not documents:
            print(f"⚠️  No extractable text found in {pdf_path}")
            continue

        cli.upsert(
            collection, documents, metadata_items=metadatas, create_collection=True
        )
        print(f"Ingested {len(documents)} chunks from {spec.title}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Ubuntu documentation PDFs")
    parser.add_argument(
        "--collection", default="ubuntu-docs", help="Target collection name"
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/ubuntu/pdf"),
        help="Directory to store downloaded PDFs",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=1800, help="Maximum characters per chunk"
    )
    parser.add_argument(
        "--overlap", type=int, default=250, help="Characters of overlap between chunks"
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Refresh PDFs even if they already exist",
    )
    args = parser.parse_args()

    downloaded = download_documents(DOC_SPECS, args.dest, force=args.force_download)
    ingest_pdfs(
        DOC_SPECS,
        downloaded,
        collection=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
