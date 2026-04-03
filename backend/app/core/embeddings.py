"""Dense embedding helpers for local indexing stages."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.config import get_settings


class EmbeddingError(RuntimeError):
    """Raised when dense embeddings cannot be produced."""


@dataclass(frozen=True)
class DenseEmbedding:
    """Single dense vector embedding produced for a chunk of text."""

    text: str
    vector: list[float]


def _hash_word_to_bucket(word: str, *, dimensions: int) -> tuple[int, float]:
    """Map a token deterministically into an embedding bucket and sign."""

    digest = hashlib.sha256(word.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % dimensions
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return bucket, sign


def build_dense_embedding(text: str, *, dimensions: int) -> list[float]:
    """Build a deterministic dense vector suitable for local indexing tests."""

    normalized = text.strip()
    if not normalized:
        raise EmbeddingError("Cannot embed empty text.")

    vector = [0.0] * dimensions
    words = normalized.casefold().split()
    for word in words:
        bucket, sign = _hash_word_to_bucket(word, dimensions=dimensions)
        vector[bucket] += sign

    magnitude = sum(component * component for component in vector) ** 0.5
    if magnitude == 0:
        raise EmbeddingError("Deterministic embedding produced a zero vector.")
    return [component / magnitude for component in vector]


async def embed_texts(texts: list[str]) -> list[DenseEmbedding]:
    """Embed a batch of texts using the configured dense embedding backend."""

    settings = get_settings()
    dimensions = settings.dense_embedding_dimensions

    if settings.embedding_backend == "gemini_v1":
        from app.core.gemini_embeddings import (
            GeminiEmbeddingError,
            embed_texts_gemini,
        )

        try:
            return await embed_texts_gemini(texts)
        except GeminiEmbeddingError:
            pass

    if settings.embedding_backend == "openai_compatible_v1":
        from app.core.openai_embeddings import (
            OpenAICompatibleEmbeddingError,
            embed_texts_openai_compatible,
        )

        try:
            return await embed_texts_openai_compatible(texts)
        except OpenAICompatibleEmbeddingError:
            pass

    return [
        DenseEmbedding(text=text, vector=build_dense_embedding(text, dimensions=dimensions))
        for text in texts
    ]
