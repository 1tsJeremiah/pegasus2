"""Lightweight Meilisearch client helpers for Codex agents."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from meilisearch import Client as MeiliClient
from meilisearch.errors import MeilisearchApiError

DEFAULT_BASE_URL = os.environ.get("CODEX_MEILI_URL", "http://127.0.0.1:7700")
DEFAULT_API_KEY = os.environ.get("CODEX_MEILI_API_KEY")
DEFAULT_INDEX = os.environ.get("CODEX_MEILI_INDEX", "codex_os_search")


@dataclass
class KeywordSearchClient:
    """Thin wrapper around the Meilisearch Python client."""

    base_url: str = DEFAULT_BASE_URL
    api_key: Optional[str] = DEFAULT_API_KEY
    index_name: str = DEFAULT_INDEX

    def __post_init__(self) -> None:
        self._client = MeiliClient(self.base_url, self.api_key)

    @property
    def raw(self) -> MeiliClient:
        return self._client

    def index(self, index: Optional[str] = None):
        name = index or self.index_name
        return self._client.index(name)

    # ------------------------------------------------------------------
    # Management helpers
    # ------------------------------------------------------------------

    def ensure_index(
        self,
        index: Optional[str] = None,
        *,
        primary_key: str = "id",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = index or self.index_name
        try:
            handle = self._client.get_index(target)
        except MeilisearchApiError:
            handle = self._client.create_index(target, {"primaryKey": primary_key})
        if settings:
            handle.update_settings(settings)
        return handle.get_raw_info()

    def delete_index(self, index: Optional[str] = None) -> None:
        target = index or self.index_name
        try:
            self._client.delete_index(target)
        except MeilisearchApiError:
            pass

    def list_indexes(self) -> List[Dict[str, Any]]:
        return self._client.get_indexes()

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def add_documents(
        self,
        documents: Iterable[Dict[str, Any]],
        *,
        index: Optional[str] = None,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        collection = list(documents)
        target = self.index(index)
        response: Optional[Dict[str, Any]] = None
        for start in range(0, len(collection), batch_size):
            chunk = collection[start : start + batch_size]
            if not chunk:
                continue
            response = target.add_documents(chunk)
        return response or {"status": "enqueued", "total": len(collection)}

    def search(
        self, query: str, *, index: Optional[str] = None, limit: int = 20
    ) -> Dict[str, Any]:
        handle = self.index(index)
        return handle.search(query, {"limit": limit})

    def health(self) -> Dict[str, Any]:
        return self._client.health()

    def version(self) -> Dict[str, Any]:
        return self._client.get_version()
