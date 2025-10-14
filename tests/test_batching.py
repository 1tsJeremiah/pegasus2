from typing import Dict, Iterable, List, Optional, Sequence, Set

import pytest

from codex_vector.client import CodexVectorClient, _ChromaBackend


class _StubBackend:
    def __init__(self) -> None:
        self.created_collections: Set[str] = set()
        self.upsert_calls: List[Dict[str, Sequence[str]]] = []
        self.current_ids: Set[str] = set()

    def status(self) -> Dict[str, str]:
        return {}

    def create_collection(self, name: str) -> Dict[str, str]:
        self.created_collections.add(name)
        return {"id": name, "name": name}

    def ensure_collection(self, name: str) -> str:
        self.created_collections.add(name)
        return name

    def resolve_collection(self, name_or_id: str) -> str:
        return name_or_id

    def collection_count(self, collection_id: str) -> int:
        return 0

    def existing_ids(self, collection_id: str, ids: Sequence[str]) -> Set[str]:
        return {doc_id for doc_id in ids if doc_id in self.current_ids}

    def upsert(
        self,
        collection_id: str,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[Dict[str, object]],
    ) -> None:
        self.upsert_calls.append(
            {
                "collection": collection_id,
                "ids": list(ids),
                "documents": list(documents),
                "metadatas": list(metadatas),
            }
        )
        self.current_ids.update(ids)

    def query(self, collection_id: str, embedding: Sequence[float], *, limit: int) -> List[Dict[str, object]]:
        return []

    def iter_metadata(self, collection_id: str, *, batch_size: int = 500) -> Iterable[Dict[str, object]]:
        return []


def test_upsert_chunking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("codex_vector.client.UPSERT_BATCH_SIZE", 2)
    client = CodexVectorClient(base_url="http://localhost:8000/api/v2")
    backend = _StubBackend()
    client._adapter = backend  # type: ignore[attr-defined]
    client._embed_documents = lambda docs: [[float(idx)] for idx, _ in enumerate(docs)]  # type: ignore[assignment]

    docs = [f"doc-{idx}" for idx in range(5)]
    client.upsert("collection", docs, create_collection=True)

    assert len(backend.upsert_calls) == 3
    assert all(len(call["ids"]) <= 2 for call in backend.upsert_calls)
    total_ids = sum(len(call["ids"]) for call in backend.upsert_calls)
    assert total_ids == len(docs)


def test_chroma_existing_id_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("codex_vector.client.EXISTING_ID_BATCH_SIZE", 3)
    backend = _ChromaBackend(base_url="http://localhost:8000/api/v2", tenant="t", database="d")

    captured_limits: List[int] = []

    def fake_request(method: str, path: str, *, payload: Optional[dict] = None, params: Optional[dict] = None):
        assert method == "POST"
        captured_limits.append(payload["limit"])
        return {"ids": payload["ids"]}

    monkeypatch.setattr(backend, "_request", fake_request)
    result = backend.existing_ids("collection", [f"id-{idx}" for idx in range(7)])

    assert captured_limits == [3, 3, 1]
    assert result == {f"id-{idx}" for idx in range(7)}


def test_doc_id_fields_enable_overwrite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("codex_vector.client.DOC_ID_FIELDS", ("source", "position"))
    monkeypatch.setattr("codex_vector.client.OVERWRITE_EXISTING", True)
    client = CodexVectorClient(base_url="http://localhost:8000/api/v2")
    backend = _StubBackend()
    client._adapter = backend  # type: ignore[attr-defined]
    client._embed_documents = lambda docs: [[float(idx)] for idx, _ in enumerate(docs)]  # type: ignore[assignment]

    client.upsert("collection", ["alpha"], metadata_source="example", create_collection=True)
    first_ids = backend.upsert_calls[0]["ids"]
    backend.upsert_calls.clear()

    client.upsert("collection", ["beta"], metadata_source="example")

    assert len(backend.upsert_calls) == 1
    assert backend.upsert_calls[0]["ids"] == first_ids
    assert backend.upsert_calls[0]["documents"][0] == "beta"
