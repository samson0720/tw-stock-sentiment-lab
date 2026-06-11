from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str]) -> np.ndarray:
    """Returns L2-normalised embeddings, shape (n, 1024)."""
    return _model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
