"""Lazy embedding model loading keeps imports and test discovery lightweight."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model():
    return SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding text cannot be empty.")
    return _get_model().encode(text).tolist()
