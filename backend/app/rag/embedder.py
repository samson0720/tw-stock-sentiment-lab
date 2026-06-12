from __future__ import annotations

from functools import lru_cache

import numpy as np

MODEL_NAME = "BAAI/bge-m3"

try:
    from sentence_transformers import SentenceTransformer as _ST
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def is_available() -> bool:
    return _AVAILABLE


@lru_cache(maxsize=1)
def _model():
    if not _AVAILABLE:
        raise RuntimeError("sentence-transformers not installed; RAG embedding unavailable")
    return _ST(MODEL_NAME)


def embed(texts: list[str]) -> np.ndarray:
    """Returns L2-normalised embeddings, shape (n, 1024)."""
    return _model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
