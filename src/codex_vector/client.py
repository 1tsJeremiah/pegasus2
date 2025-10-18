"""HTTP client for interacting with the Codex Chroma vector database."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .embeddings import (DEFAULT_DIMENSION, generate_embedding, get_dimension,
                         get_model_name, load_sentence_transformer)

DEFAULT_BASE_URL = os.environ.get(
    "CODEX_VECTOR_BASE_URL", "http://127.0.0.1:8000/api/v2"
)
DEFAULT_TENANT = os.environ.get("CODEX_VECTOR_TENANT", "default_tenant")
DEFAULT_DATABASE = os.environ.get("CODEX_VECTOR_DB", "default_database")


@lru_cache(maxsize=1)
def _load_embedder():
    """Attempt to initialise a high-fidelity embedding model."""

    return load_sentence_transformer(get_model_name())


@dataclass
class CLIResult:
    status: int
    payload: Optional[dict]
    raw: str


class CodexVectorClient:
    """Lightweight wrapper around the Chroma REST API with deterministic embeddings."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
        *,
        dimension: Optional[int] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant = tenant
        self.database = database
        self.dimension = dimension or get_dimension(DEFAULT_DIMENSION)
        self._embedder = _load_embedder()
        self._embedder_failed = False

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _tenant_path(self, suffix: str) -> str:
        return f"/tenants/{self.tenant}/databases/{self.database}{suffix}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> CLIResult:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(
            url, data=data, method=method, headers={"Content-Type": "application/json"}
        )

        try:
            with urlopen(req, timeout=10) as resp:
                content = resp.read().decode()
                try:
                    parsed = json.loads(content) if content else None
                except json.JSONDecodeError:
                    parsed = None
                return CLIResult(status=resp.status, payload=parsed, raw=content)
        except HTTPError as exc:  # pragma: no cover - runtime guard
            body = exc.read().decode()
            raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body}") from exc
        except URLError as exc:  # pragma: no cover - runtime guard
            raise RuntimeError(f"Connection failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def status(self) -> None:
        identity = self._request("GET", "/auth/identity")
        collections = self._request("GET", self._tenant_path("/collections"))

        print("Codex Vector Database Status")
        print("============================")
        print(f"Base URL : {self.base_url}")
        print(f"Tenant   : {self.tenant}")
        print(f"Database : {self.database}")
        user_id = identity.payload.get("user_id") if identity.payload else "unknown"
        print(f"User     : {user_id!r}")
        print()
        print("Collections:")
        payload = collections.payload or []
        if not payload:
            print("  (none)")
            return
        for entry in payload:
            count = self._collection_count(entry["id"])
            print(f"  - {entry['name']} ({entry['id']}) :: docs={count}")

    def create_collection(self, name: str) -> None:
        result = self._request(
            "POST",
            self._tenant_path("/collections"),
            payload={"name": name},
        )
        payload = result.payload or {}
        print(f"Created collection {payload.get('name')} :: id={payload.get('id')}")

    def get_collection_id(self, name_or_id: str) -> str:
        collections = (
            self._request("GET", self._tenant_path("/collections")).payload or []
        )
        for entry in collections:
            if entry["id"] == name_or_id or entry["name"] == name_or_id:
                return entry["id"]
        raise RuntimeError(f"Collection '{name_or_id}' not found")

    def ensure_collection(self, name: str) -> str:
        collections = (
            self._request("GET", self._tenant_path("/collections")).payload or []
        )
        for entry in collections:
            if entry["name"] == name:
                return entry["id"]
        created = self._request(
            "POST",
            self._tenant_path("/collections"),
            payload={"name": name},
        )
        payload = created.payload or {}
        return payload.get("id") or name

    def upsert(
        self,
        name_or_id: str,
        documents: Iterable[str],
        *,
        metadata_source: Optional[str] = None,
        metadata_items: Optional[List[dict]] = None,
        create_collection: bool = False,
    ) -> None:
        if create_collection:
            collection_id = self.ensure_collection(name_or_id)
        else:
            collection_id = self.get_collection_id(name_or_id)

        docs = list(documents)
        if not docs:
            raise RuntimeError("No documents provided")

        if metadata_items is not None and len(metadata_items) != len(docs):
            raise RuntimeError("metadata_items must match number of documents")

        embeddings = self._embed_documents(docs)
        payload: Dict[str, Any] = {
            "ids": [
                self._stable_doc_id(
                    text,
                    (
                        json.dumps(metadata_items[idx], sort_keys=True)
                        if metadata_items
                        else metadata_source
                    ),
                )
                for idx, text in enumerate(docs)
            ],
            "documents": docs,
            "embeddings": embeddings,
        }
        if metadata_items:
            payload["metadatas"] = metadata_items
        elif metadata_source:
            payload["metadatas"] = [{"source": metadata_source} for _ in docs]

        self._request(
            "POST",
            self._tenant_path(f"/collections/{collection_id}/upsert"),
            payload=payload,
        )
        print(f"Upserted {len(docs)} document(s) into collection '{name_or_id}'")

    def query(self, name_or_id: str, query_text: str, *, limit: int = 5) -> None:
        collection_id = self.get_collection_id(name_or_id)
        embedding = self._embed_documents([query_text])[0]
        payload = {
            "query_embeddings": [embedding],
            "n_results": limit,
            "include": ["documents", "metadatas", "distances"],
        }
        response = self._request(
            "POST",
            self._tenant_path(f"/collections/{collection_id}/query"),
            payload=payload,
        )
        print(f"Query results for '{query_text}':")
        results = self._parse_query_results(response.payload)

        if not results:
            print("  (no matches)")
            return

        for result in results:
            dist = result.get("distance")
            distance_repr = (
                f"{dist:.4f}" if isinstance(dist, (int, float)) else str(dist or "?")
            )
            print(f"  - distance={distance_repr} :: {result['document']}")
            if result.get("metadata"):
                print(f"      metadata={result['metadata']}")

    def query_results(
        self, name_or_id: str, query_text: str, *, limit: int = 5
    ) -> List[dict]:
        collection_id = self.get_collection_id(name_or_id)
        embedding = self._embed_documents([query_text])[0]
        response = self._request(
            "POST",
            self._tenant_path(f"/collections/{collection_id}/query"),
            payload={
                "query_embeddings": [embedding],
                "n_results": limit,
                "include": ["documents", "metadatas", "distances"],
            },
        )
        return self._parse_query_results(response.payload)

    def iter_metadata(
        self, name_or_id: str, *, batch_size: int = 500
    ) -> Iterable[Dict[str, Any]]:
        collection_id = self.get_collection_id(name_or_id)
        offset = 0
        while True:
            payload = {
                "include": ["metadatas"],
                "limit": batch_size,
                "offset": offset,
            }
            response = self._request(
                "POST",
                self._tenant_path(f"/collections/{collection_id}/get"),
                payload=payload,
            )
            metadatas = self._extract_metadatas(response.payload)
            if not metadatas:
                break
            for meta in metadatas:
                yield meta or {}
            if len(metadatas) < batch_size:
                break
            offset += batch_size

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed_documents(self, docs: List[str]) -> List[List[float]]:
        if not docs:
            return []

        if self._embedder is not None and not self._embedder_failed:
            try:
                vectors = self._embedder.encode(docs, convert_to_numpy=True)
            except Exception:  # pragma: no cover - runtime guard
                self._embedder_failed = True
            else:
                return [vector.tolist() for vector in vectors]

        return [generate_embedding(text, self.dimension) for text in docs]

    @staticmethod
    def _stable_doc_id(content: str, namespace: Optional[str] = None) -> str:
        import hashlib

        hasher = hashlib.blake2b(digest_size=6)
        if namespace:
            hasher.update(namespace.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        return f"doc-{hasher.hexdigest()}"

    def _collection_count(self, collection_id: str) -> int:
        response = self._request(
            "GET",
            self._tenant_path(f"/collections/{collection_id}/count"),
        )
        payload = response.payload
        if isinstance(payload, dict) and "count" in payload:
            return int(payload["count"])
        if isinstance(payload, int):
            return payload
        try:
            return int(payload)
        except (TypeError, ValueError):
            return 0

    def _parse_query_results(self, payload: Optional[dict]) -> List[dict]:
        payload = payload or {}
        raw_results: List[dict] = []
        if isinstance(payload, dict) and "results" in payload:
            raw_results = payload.get("results", []) or []
        elif isinstance(payload, dict):
            raw_results = [
                {
                    "documents": payload.get("documents"),
                    "distances": payload.get("distances"),
                    "metadatas": payload.get("metadatas"),
                }
            ]

        if not raw_results:
            return []

        first = raw_results[0]
        docs = (first.get("documents") or [[]])[0] or []
        dists = (first.get("distances") or [[]])[0] or []
        metas = (first.get("metadatas") or [[]])[0] or []

        results: List[dict] = []
        for idx, doc in enumerate(docs):
            distance = dists[idx] if idx < len(dists) else None
            metadata = metas[idx] if idx < len(metas) else {}
            results.append(
                {"document": doc, "distance": distance, "metadata": metadata}
            )
        return results

    @staticmethod
    def _extract_metadatas(payload: Optional[dict]) -> List[Dict[str, Any]]:
        payload = payload or {}
        metadatas = payload.get("metadatas") or []
        if not metadatas:
            return []
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
            flattened: List[Dict[str, Any]] = []
            for item in metadatas:
                if isinstance(item, list):
                    flattened.extend(item)
                elif isinstance(item, dict):
                    flattened.append(item)
            return flattened
        return metadatas


__all__ = [
    "CodexVectorClient",
    "DEFAULT_BASE_URL",
    "DEFAULT_TENANT",
    "DEFAULT_DATABASE",
]
