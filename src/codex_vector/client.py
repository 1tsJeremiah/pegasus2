"""Unified client for interacting with the Mindstack vector backends.

The original implementation only supported the Mindstack Core (Chroma) HTTP API.
This module now abstracts the backend so production deployments can target
Qdrant while development environments continue using Chroma. Incremental
upserts, reusable embedding helpers, and metadata iteration are provided in a
backend-agnostic fashion.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from .embeddings import (DEFAULT_DIMENSION, generate_embedding, get_dimension,
                         get_model_name, load_sentence_transformer)

DEFAULT_BASE_URL = os.environ.get(
    "CODEX_VECTOR_BASE_URL", "http://127.0.0.1:8000/api/v2"
)
DEFAULT_TENANT = os.environ.get("CODEX_VECTOR_TENANT", "default_tenant")
DEFAULT_DATABASE = os.environ.get("CODEX_VECTOR_DB", "default_database")
DEFAULT_BACKEND = os.environ.get("CODEX_VECTOR_BACKEND", "auto").lower()


def _env_flag(name: str, default: bool = False) -> bool:
    """Read boolean-ish env flags (accepts 1/true/yes/on)."""

    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read positive integer env values with a safe default."""

    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _chunk_items(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


EXISTING_ID_BATCH_SIZE = _env_int("CODEX_VECTOR_EXISTING_ID_BATCH", 256)
UPSERT_BATCH_SIZE = _env_int("CODEX_VECTOR_UPSERT_BATCH", 128)
_DOC_ID_FIELDS_RAW = os.environ.get("CODEX_VECTOR_DOC_ID_FIELDS", "")
DOC_ID_FIELDS: Tuple[str, ...] = tuple(field.strip() for field in _DOC_ID_FIELDS_RAW.split(",") if field.strip())
OVERWRITE_EXISTING = _env_flag("CODEX_VECTOR_OVERWRITE_EXISTING", default=False)
HTTP_RETRIES = _env_int("CODEX_VECTOR_HTTP_RETRIES", 3)
HTTP_RETRY_DELAY = _env_int("CODEX_VECTOR_HTTP_RETRY_DELAY", 2)


# ---------------------------------------------------------------------------
# Backend adapters
# ---------------------------------------------------------------------------


class _BaseBackend:
    """Interface implemented by backend-specific adapters."""

    name: str = "unknown"

    def status(self) -> Dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError

    def create_collection(self, name: str) -> Dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError

    def ensure_collection(self, name: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def resolve_collection(self, name_or_id: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def collection_count(self, collection_id: str) -> int:  # pragma: no cover - abstract
        raise NotImplementedError

    def existing_ids(self, collection_id: str, ids: Sequence[str]) -> Set[str]:  # pragma: no cover - abstract
        raise NotImplementedError

    def upsert(
        self,
        collection_id: str,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[Dict[str, Any]],
    ) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def query(self, collection_id: str, embedding: Sequence[float], *, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError  # pragma: no cover - abstract

    def iter_metadata(self, collection_id: str, *, batch_size: int = 500) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError  # pragma: no cover - abstract


class _ChromaBackend(_BaseBackend):
    name = "chroma"

    def __init__(self, *, base_url: str, tenant: str, database: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant = tenant
        self.database = database

    # -------------------------- HTTP plumbing --------------------------

    def _tenant_path(self, suffix: str) -> str:
        return f"/tenants/{self.tenant}/databases/{self.database}{suffix}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Dict[str, Any]:
        import json as _json
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        data = _json.dumps(payload).encode() if payload is not None else None
        req = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})

        last_error: Optional[Exception] = None
        attempts = max(1, HTTP_RETRIES)
        for attempt in range(1, attempts + 1):
            try:
                with urlopen(req, timeout=10) as resp:
                    content = resp.read().decode()
                    if not content:
                        return {"status": resp.status}
                    try:
                        return _json.loads(content)
                    except _json.JSONDecodeError:
                        return {"status": resp.status, "raw": content}
            except HTTPError as exc:  # pragma: no cover - runtime guard
                body = exc.read().decode()
                raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body}") from exc
            except URLError as exc:  # pragma: no cover - runtime guard
                last_error = RuntimeError(f"Connection failed: {exc}")
            except TimeoutError as exc:  # pragma: no cover - runtime guard
                last_error = RuntimeError(f"Connection timed out: {exc}")

            if attempt < attempts:
                time.sleep(max(1, HTTP_RETRY_DELAY))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Mindstack request failed without specific error")

    # ------------------------------ API -------------------------------

    def status(self) -> Dict[str, Any]:
        identity = self._request("GET", "/auth/identity")
        collections = self._request("GET", self._tenant_path("/collections")).get("collections", []) or []

        items: List[Dict[str, Any]] = []
        for entry in collections:
            count = self.collection_count(entry["id"])
            items.append({"name": entry["name"], "id": entry["id"], "count": count})

        return {
            "backend": self.name,
            "base_url": self.base_url,
            "tenant": self.tenant,
            "database": self.database,
            "user": (identity or {}).get("user_id", "unknown"),
            "collections": items,
        }

    def create_collection(self, name: str) -> Dict[str, Any]:
        payload = {"name": name}
        response = self._request(
            "POST",
            self._tenant_path("/collections"),
            payload=payload,
        )
        return response or payload

    def ensure_collection(self, name: str) -> str:
        collections = self._request("GET", self._tenant_path("/collections")).get("collections", []) or []
        for entry in collections:
            if entry["name"] == name:
                return entry["id"]
        created = self.create_collection(name)
        return created.get("id") or name

    def resolve_collection(self, name_or_id: str) -> str:
        collections = self._request("GET", self._tenant_path("/collections")).get("collections", []) or []
        for entry in collections:
            if entry["id"] == name_or_id or entry["name"] == name_or_id:
                return entry["id"]
        raise RuntimeError(f"Collection '{name_or_id}' not found")

    def collection_count(self, collection_id: str) -> int:
        response = self._request(
            "GET",
            self._tenant_path(f"/collections/{collection_id}/count"),
        )
        payload = response.get("count", response)
        try:
            return int(payload)
        except (TypeError, ValueError):
            return 0

    def existing_ids(self, collection_id: str, ids: Sequence[str]) -> Set[str]:
        if not ids:
            return set()
        matches: Set[str] = set()
        for chunk in _chunk_items(list(ids), EXISTING_ID_BATCH_SIZE):
            response = self._request(
                "POST",
                self._tenant_path(f"/collections/{collection_id}/get"),
                payload={"ids": list(chunk), "limit": len(chunk)},
            )
            raw_ids = response.get("ids") or []
            if raw_ids and isinstance(raw_ids[0], list):
                raw_ids = raw_ids[0]
            matches.update(str(entry) for entry in raw_ids)
        return matches

    def upsert(
        self,
        collection_id: str,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[Dict[str, Any]],
    ) -> None:
        payload: Dict[str, Any] = {
            "ids": list(ids),
            "documents": list(documents),
            "embeddings": list(embeddings),
        }
        if metadatas:
            payload["metadatas"] = list(metadatas)

        self._request(
            "POST",
            self._tenant_path(f"/collections/{collection_id}/upsert"),
            payload=payload,
        )

    def query(self, collection_id: str, embedding: Sequence[float], *, limit: int) -> List[Dict[str, Any]]:
        response = self._request(
            "POST",
            self._tenant_path(f"/collections/{collection_id}/query"),
            payload={
                "query_embeddings": [list(embedding)],
                "n_results": limit,
                "include": ["documents", "metadatas", "distances"],
            },
        )
        return self._parse_query_results(response)

    def iter_metadata(self, collection_id: str, *, batch_size: int = 500) -> Iterable[Dict[str, Any]]:
        offset = 0
        while True:
            response = self._request(
                "POST",
                self._tenant_path(f"/collections/{collection_id}/get"),
                payload={"include": ["metadatas"], "limit": batch_size, "offset": offset},
            )
            metadatas = self._extract_metadatas(response)
            if not metadatas:
                break
            for meta in metadatas:
                yield meta
            if len(metadatas) < batch_size:
                break
            offset += batch_size

    @staticmethod
    def _extract_metadatas(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = payload or {}
        metadatas = payload.get("metadatas") or []
        if not metadatas:
            return []
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
            flattened: List[Dict[str, Any]] = []
            for item in metadatas:
                if isinstance(item, list):
                    flattened.extend(obj for obj in item if isinstance(obj, dict))
                elif isinstance(item, dict):
                    flattened.append(item)
            return flattened
        return [meta for meta in metadatas if isinstance(meta, dict)]

    @staticmethod
    def _parse_query_results(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = payload or {}
        if "results" in payload:
            raw_results = payload.get("results") or []
        else:
            raw_results = [payload]
        if not raw_results:
            return []
        first = raw_results[0]
        docs = (first.get("documents") or [[]])[0] or []
        dists = (first.get("distances") or [[]])[0] or []
        metas = (first.get("metadatas") or [[]])[0] or []
        results: List[Dict[str, Any]] = []
        for idx, doc in enumerate(docs):
            distance = dists[idx] if idx < len(dists) else None
            metadata = metas[idx] if idx < len(metas) else {}
            results.append({"document": doc, "distance": distance, "metadata": metadata})
        return results


class _QdrantBackend(_BaseBackend):
    name = "qdrant"

    def __init__(self, *, base_url: str, dimension: int, api_key: Optional[str] = None) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qmodels
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "qdrant-client is required. Install the project requirements before targeting Qdrant."
            ) from exc

        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"http://{base_url}"
            parsed = urlparse(base_url)

        self._raw_base_url = base_url.rstrip("/")
        prefer_grpc = _env_flag("CODEX_QDRANT_USE_GRPC", default=True)
        grpc_port_env = os.environ.get("CODEX_QDRANT_GRPC_PORT")
        grpc_port: Optional[int] = None
        if prefer_grpc:
            if grpc_port_env:
                try:
                    grpc_port = int(grpc_port_env)
                except ValueError:
                    grpc_port = None
            elif parsed.port and parsed.port < 65535:
                grpc_port = parsed.port + 1

        client_kwargs: Dict[str, Any] = {
            "url": self._raw_base_url,
            "api_key": api_key,
            "timeout": 10.0,
            "prefer_grpc": prefer_grpc,
        }
        if prefer_grpc and grpc_port:
            client_kwargs["grpc_port"] = grpc_port

        self._client = QdrantClient(**client_kwargs)
        self._models = qmodels
        self._dimension = dimension
        self._prefer_grpc = prefer_grpc and bool(getattr(self._client, "_grpc_client", None))

    def status(self) -> Dict[str, Any]:
        collections_resp = self._client.get_collections()
        collections: List[Dict[str, Any]] = []
        for entry in collections_resp.collections or []:
            name = entry.name
            collections.append({"name": name, "id": name, "count": self.collection_count(name)})

        return {
            "backend": self.name,
            "base_url": self._raw_base_url,
            "transport": "grpc" if self._prefer_grpc else "http",
            "collections": collections,
            "user": None,
        }

    def create_collection(self, name: str) -> Dict[str, Any]:
        if not self._client.collection_exists(name):
            vector_params = self._models.VectorParams(size=self._dimension, distance=self._models.Distance.COSINE)
            self._client.create_collection(collection_name=name, vectors_config=vector_params)
        return {"name": name, "id": name}

    def ensure_collection(self, name: str) -> str:
        if not self._client.collection_exists(name):
            self.create_collection(name)
        return name

    def resolve_collection(self, name_or_id: str) -> str:
        if not self._client.collection_exists(name_or_id):
            raise RuntimeError(f"Collection '{name_or_id}' not found")
        return name_or_id

    def collection_count(self, collection_id: str) -> int:
        response = self._client.count(collection_name=collection_id, exact=True)
        return int(getattr(response, "count", 0))

    def existing_ids(self, collection_id: str, ids: Sequence[str]) -> Set[str]:
        if not ids:
            return set()
        matches: Set[str] = set()
        for chunk in _chunk_items(list(ids), EXISTING_ID_BATCH_SIZE):
            records = self._client.retrieve(
                collection_name=collection_id,
                ids=list(chunk),
                with_payload=False,
            )
            matches.update(str(record.id) for record in records)
        return matches

    def upsert(
        self,
        collection_id: str,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[Dict[str, Any]],
    ) -> None:
        points = []
        for doc_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas):
            payload = dict(metadata)
            payload["document"] = document
            points.append(self._models.PointStruct(id=doc_id, vector=list(embedding), payload=payload))
        self._client.upsert(collection_name=collection_id, points=points)

    def query(self, collection_id: str, embedding: Sequence[float], *, limit: int) -> List[Dict[str, Any]]:
        results = self._client.search(
            collection_name=collection_id,
            query_vector=list(embedding),
            limit=limit,
            with_payload=True,
        )
        formatted: List[Dict[str, Any]] = []
        for entry in results:
            payload = entry.payload or {}
            metadata = {key: value for key, value in payload.items() if key != "document"}
            document = payload.get("document", "")
            formatted.append(
                {
                    "document": document,
                    "distance": entry.score,
                    "metadata": metadata,
                }
            )
        return formatted

    def iter_metadata(self, collection_id: str, *, batch_size: int = 500) -> Iterable[Dict[str, Any]]:
        next_offset = None
        while True:
            records, next_offset = self._client.scroll(
                collection_name=collection_id,
                limit=batch_size,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
            )
            if not records:
                break
            for record in records:
                payload = record.payload or {}
                metadata = {key: value for key, value in payload.items() if key != "document"}
                metadata.setdefault("doc_id", str(record.id))
                yield metadata
            if next_offset is None:
                break


# ---------------------------------------------------------------------------
# Public Codex client
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_embedder():
    """Attempt to initialise a high-fidelity embedding model."""

    return load_sentence_transformer(get_model_name())


class CodexVectorClient:
    """Backend-aware client with deterministic fallback embeddings."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
        *,
        dimension: Optional[int] = None,
        backend: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant = tenant
        self.database = database
        self.dimension = dimension or get_dimension(DEFAULT_DIMENSION)

        resolved_backend = self._select_backend(backend or DEFAULT_BACKEND, self.base_url)
        self.backend_name = resolved_backend

        if resolved_backend == "qdrant":
            api_key = os.environ.get("CODEX_QDRANT_API_KEY") or os.environ.get("QDRANT_API_KEY")
            self._adapter: _BaseBackend = _QdrantBackend(
                base_url=self.base_url,
                dimension=self.dimension,
                api_key=api_key,
            )
        else:
            if "/api/" not in self.base_url:
                # Backwards compatibility: Chroma HTTP API typically lives at /api/v2
                self.base_url = f"{self.base_url.rstrip('/')}/api/v2"
            self._adapter = _ChromaBackend(base_url=self.base_url, tenant=self.tenant, database=self.database)

        self._embedder = _load_embedder()
        self._embedder_failed = False

    # ---------------------------- API surface ----------------------------

    def status(self) -> None:
        summary = self._adapter.status()
        backend = summary.get("backend", self.backend_name)
        print("Codex Vector Database Status")
        print("============================")
        print(f"Backend  : {backend}")
        print(f"Base URL : {summary.get('base_url', self.base_url)}")
        transport = summary.get("transport")
        if transport:
            print(f"Transport: {transport}")
        if backend == "chroma":
            print(f"Tenant   : {summary.get('tenant', self.tenant)}")
            print(f"Database : {summary.get('database', self.database)}")
        user = summary.get("user")
        if user:
            print(f"User     : {user}")
        print()
        print("Collections:")
        collections = summary.get("collections") or []
        if not collections:
            print("  (none)")
        else:
            for entry in collections:
                print(f"  - {entry['name']} ({entry['id']}) :: docs={entry['count']}")

    def create_collection(self, name: str) -> None:
        result = self._adapter.create_collection(name)
        print(f"Created collection {result.get('name', name)} :: id={result.get('id', name)}")

    def get_collection_id(self, name_or_id: str) -> str:
        return self._adapter.resolve_collection(name_or_id)

    def ensure_collection(self, name: str) -> str:
        return self._adapter.ensure_collection(name)

    def collection_count(self, name_or_id: str) -> int:
        collection_id = self.get_collection_id(name_or_id)
        return self._adapter.collection_count(collection_id)

    def upsert(
        self,
        name_or_id: str,
        documents: Iterable[str],
        *,
        metadata_source: Optional[str] = None,
        metadata_items: Optional[List[dict]] = None,
        create_collection: bool = False,
    ) -> None:
        docs = [doc for doc in documents if doc]
        if not docs:
            raise RuntimeError("No documents provided")

        if metadata_items is not None and len(metadata_items) != len(docs):
            raise RuntimeError("metadata_items must match number of documents")

        if create_collection:
            collection_id = self.ensure_collection(name_or_id)
        else:
            collection_id = self.get_collection_id(name_or_id)

        prepared_metadatas: List[Dict[str, Any]] = []
        doc_ids: List[str] = []

        for idx, doc in enumerate(docs):
            base_meta: Dict[str, Any] = {}
            if metadata_items:
                base_meta.update(metadata_items[idx] or {})
            elif metadata_source:
                base_meta["source"] = metadata_source

            if metadata_source and "source" not in base_meta:
                base_meta["source"] = metadata_source
            base_meta.setdefault("position", idx)

            existing_doc_id = base_meta.get("doc_id")
            if isinstance(existing_doc_id, str) and existing_doc_id:
                doc_id = existing_doc_id
            else:
                doc_id = self._build_doc_id(doc, base_meta, metadata_source)
                base_meta.setdefault("doc_id", doc_id)

            prepared_metadatas.append(base_meta)
            doc_ids.append(doc_id)

        existing = self._adapter.existing_ids(collection_id, doc_ids)
        if existing and len(existing) == len(doc_ids) and not OVERWRITE_EXISTING:
            print(
                f"Upsert skipped: all {len(doc_ids)} document(s) already present in '{name_or_id}'."
            )
            return

        docs_to_upsert: List[str] = []
        metas_to_upsert: List[Dict[str, Any]] = []
        ids_to_upsert: List[str] = []
        skipped = 0
        replaced = 0
        for doc, meta, doc_id in zip(docs, prepared_metadatas, doc_ids):
            if doc_id in existing:
                if not OVERWRITE_EXISTING:
                    skipped += 1
                    continue
                replaced += 1
            docs_to_upsert.append(doc)
            metas_to_upsert.append(meta)
            ids_to_upsert.append(doc_id)

        if not ids_to_upsert:
            message = f"Upsert skipped: no new documents for collection '{name_or_id}'."
            if skipped:
                message += f" (skipped {skipped} existing)"
            print(message)
            return

        total_upserted = 0
        for offset in range(0, len(ids_to_upsert), UPSERT_BATCH_SIZE):
            batch_ids = ids_to_upsert[offset : offset + UPSERT_BATCH_SIZE]
            batch_docs = docs_to_upsert[offset : offset + UPSERT_BATCH_SIZE]
            batch_metas = metas_to_upsert[offset : offset + UPSERT_BATCH_SIZE]
            embeddings = self._embed_documents(batch_docs)
            if not embeddings:
                continue
            self._adapter.upsert(
                collection_id,
                batch_ids,
                batch_docs,
                embeddings,
                batch_metas,
            )
            total_upserted += len(batch_ids)

        message = f"Upserted {total_upserted} document(s) into collection '{name_or_id}'"
        details: List[str] = []
        if replaced:
            details.append(f"replaced {replaced} existing")
        if skipped:
            details.append(f"skipped {skipped} existing")
        if details:
            message += " (" + ", ".join(details) + ")"
        print(message)

    def query(self, name_or_id: str, query_text: str, *, limit: int = 5) -> None:
        results = self.query_results(name_or_id, query_text, limit=limit)
        print(f"Query results for '{query_text}':")
        if not results:
            print("  (no matches)")
            return
        for result in results:
            distance = result.get("distance")
            distance_repr = f"{distance:.4f}" if isinstance(distance, (int, float)) else str(distance or "?")
            document = result.get("document", "")
            metadata = result.get("metadata") or {}
            print(f"  - distance={distance_repr} :: {document}")
            if metadata:
                print(f"      metadata={metadata}")

    def query_results(
        self, name_or_id: str, query_text: str, *, limit: int = 5
    ) -> List[dict]:
        collection_id = self.get_collection_id(name_or_id)
        embedding = self._embed_documents([query_text])[0]
        return self._adapter.query(collection_id, embedding, limit=limit)

    def iter_metadata(
        self, name_or_id: str, *, batch_size: int = 500
    ) -> Iterable[Dict[str, Any]]:
        collection_id = self.get_collection_id(name_or_id)
        yield from self._adapter.iter_metadata(collection_id, batch_size=batch_size)

    # ------------------------- Internal helpers -------------------------

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

    def _build_doc_id(self, content: str, metadata: Dict[str, Any], metadata_source: Optional[str]) -> str:
        candidate = self._doc_id_from_fields(metadata)
        if candidate:
            return candidate

        namespace_meta = {key: value for key, value in metadata.items() if key != "doc_id"}
        stable_namespace = ""
        if namespace_meta:
            stable_namespace = json.dumps(namespace_meta, sort_keys=True, separators=(",", ":"), default=str)
        if not stable_namespace:
            stable_namespace = metadata_source or ""
        return self._stable_doc_id(content, stable_namespace or None)

    @staticmethod
    def _doc_id_from_fields(metadata: Dict[str, Any]) -> Optional[str]:
        if not DOC_ID_FIELDS:
            return None
        components: List[str] = []
        for field in DOC_ID_FIELDS:
            if field not in metadata:
                return None
            value = metadata[field]
            try:
                serialised = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            except TypeError:
                serialised = repr(value)
            components.append(f"{field}={serialised}")
        key = "|".join(components)
        return CodexVectorClient._stable_doc_id(key, namespace="metadata")

    @staticmethod
    def _stable_doc_id(content: str, namespace: Optional[str] = None) -> str:
        import hashlib

        hasher = hashlib.blake2b(digest_size=6)
        if namespace:
            hasher.update(namespace.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        return f"doc-{hasher.hexdigest()}"

 

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
    def _select_backend(preference: str, base_url: str) -> str:
        if preference in {"chroma", "qdrant"}:
            return preference
        if preference == "auto":
            # Check if MINDSTACK_PROFILE=production is set, which should default to Qdrant
            mindstack_profile = os.environ.get("MINDSTACK_PROFILE", "").lower()
            if mindstack_profile == "production":
                return "qdrant"
            
            target = base_url.lower()
            if "6333" in target or "qdrant" in target:
                return "qdrant"
            env_url = os.environ.get("CODEX_VECTOR_BASE_URL", "").lower()
            if env_url and ("6333" in env_url or "qdrant" in env_url):
                return "qdrant"
            return "chroma"
        return "chroma"


__all__ = [
    "CodexVectorClient",
    "DEFAULT_BASE_URL",
    "DEFAULT_TENANT",
    "DEFAULT_DATABASE",
]
