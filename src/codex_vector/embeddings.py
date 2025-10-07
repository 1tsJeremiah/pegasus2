"""Embedding utilities for the Codex vector stack."""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter
from functools import lru_cache
from typing import List, Optional

DEFAULT_DIMENSION = 384
_DEFAULT_MODEL = "all-MiniLM-L6-v2"

try:  # Optional high-quality embeddings
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore


def get_dimension(default: int = DEFAULT_DIMENSION) -> int:
    """Resolve the target embedding dimension from the environment."""

    value = os.environ.get("CODEX_VECTOR_DIM")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_model_name(default: str = _DEFAULT_MODEL) -> str:
    """Resolve the embedding model name from the environment."""

    return os.environ.get("CODEX_EMBED_MODEL", default)


@lru_cache(maxsize=2)
def load_sentence_transformer(model_name: Optional[str] = None):
    """Load a SentenceTransformer model if the dependency is available."""

    if SentenceTransformer is None:
        return None
    target = model_name or get_model_name()
    try:
        return SentenceTransformer(target)
    except Exception:
        return None


def generate_embedding(text: str, dimension: int = DEFAULT_DIMENSION) -> List[float]:
    """Generate a deterministic pseudo-embedding using Blake2b hashes."""

    if dimension <= 0:
        raise ValueError("dimension must be positive")

    tokens = re.findall(r"[\w-]+", text.lower()) or ["__empty__"]
    token_counts = Counter(tokens)

    vector = [0.0] * dimension
    for token, count in token_counts.items():
        weight = 1.0 + math.log1p(count)
        token_bytes = token.encode("utf-8")
        for idx in range(dimension):
            digest = hashlib.blake2b(
                token_bytes + idx.to_bytes(2, "little"), digest_size=8
            ).digest()
            integer = int.from_bytes(digest, "little")
            value = (integer / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0
            vector[idx] += weight * value

    norm = math.sqrt(sum(val * val for val in vector))
    if norm > 0:
        vector = [val / norm for val in vector]
    return vector


__all__ = [
    "DEFAULT_DIMENSION",
    "generate_embedding",
    "get_dimension",
    "get_model_name",
    "load_sentence_transformer",
]
