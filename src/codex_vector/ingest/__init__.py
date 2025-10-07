"""Ingestion utilities for Codex vector stack."""

from .bootstrap import main as bootstrap_main  # noqa: F401
from .official_docs import main as official_docs_main  # noqa: F401

__all__ = ["bootstrap_main", "official_docs_main"]
