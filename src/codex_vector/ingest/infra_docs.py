#!/usr/bin/env python3
"""Fetch infrastructure documentation (Cloudflare, Pi-hole, Traefik, Docker) and ingest into the vector database."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List

import requests
from bs4 import BeautifulSoup

from ..client import CodexVectorClient
from .official_docs import chunk_text

DOC_SPECS: List[Dict[str, str]] = [
    {
        "id": "cloudflare-tunnel-guide",
        "title": "Cloudflare Tunnel Guide",
        "url": "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/",
    },
    {
        "id": "cloudflare-tunnel-dns",
        "title": "Cloudflare Tunnel DNS Routing",
        "url": "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/routing-to-tunnel/dns/",
    },
    {
        "id": "pihole-docker",
        "title": "Pi-hole Docker Deployment",
        "url": "https://docs.pi-hole.net/docker/",
    },
    {
        "id": "traefik-docker-provider",
        "title": "Traefik Docker Provider",
        "url": "https://doc.traefik.io/traefik/providers/docker/",
    },
    {
        "id": "traefik-dns-challenge",
        "title": "Traefik ACME DNS Challenge",
        "url": "https://doc.traefik.io/traefik/https/acme/#dnschallenge",
    },
    {
        "id": "docker-compose-overview",
        "title": "Docker Compose Overview",
        "url": "https://docs.docker.com/compose/",
    },
]

HEADERS = {"User-Agent": "Codex-Agent/1.0 (+https://github.com/openai)"}


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    filtered: Iterable[str] = (line for line in lines if line)
    return "\n".join(filtered)


def fetch_text(spec: Dict[str, str]) -> str:
    resp = requests.get(spec["url"], headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return html_to_text(resp.text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch infrastructure docs and store in the vector DB"
    )
    parser.add_argument(
        "--collection", default="infra-docs", help="Target collection name"
    )
    parser.add_argument(
        "--max-chars", type=int, default=900, help="Chunk size for ingestion"
    )
    parser.add_argument(
        "--overlap", type=int, default=150, help="Chunk overlap for ingestion"
    )
    parser.add_argument(
        "--batch-size", type=int, default=16, help="Batch size for upserts"
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/infra/docs"),
        help="Directory to store fetched documentation",
    )
    args = parser.parse_args()

    dest_dir: Path = args.dest
    dest_dir.mkdir(parents=True, exist_ok=True)

    cli = CodexVectorClient()
    all_chunks: List[Dict[str, object]] = []

    for spec in DOC_SPECS:
        try:
            text = fetch_text(spec)
        except Exception as exc:
            print(f"⚠️  Failed to fetch {spec['url']}: {exc}")
            continue

        file_path = dest_dir / f"{spec['id']}.txt"
        file_path.write_text(text, encoding="utf-8")

        for index, chunk in enumerate(
            chunk_text(text, max_chars=args.max_chars, overlap=args.overlap),
            start=1,
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

    print(f"Ingested {len(all_chunks)} chunks into collection '{args.collection}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
