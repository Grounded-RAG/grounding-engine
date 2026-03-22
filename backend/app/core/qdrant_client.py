"""Qdrant client helpers for dense chunk indexing."""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import get_settings


class VectorStoreError(RuntimeError):
    """Raised when dense vector storage operations fail."""


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Return a cached Qdrant client using the configured endpoint."""

    settings = get_settings()
    return QdrantClient(url=str(settings.qdrant_url))


def reset_qdrant_client() -> None:
    """Clear the cached Qdrant client."""

    get_qdrant_client.cache_clear()


def ensure_qdrant_collection(*, vector_size: int) -> None:
    """Create the configured Qdrant collection if it does not exist."""

    client = get_qdrant_client()
    collection_name = get_settings().qdrant_collection
    try:
        if client.collection_exists(collection_name=collection_name):
            return
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
    except Exception as exc:  # pragma: no cover - defensive wrapper for client errors
        raise VectorStoreError("Failed to ensure Qdrant collection exists.") from exc


def upsert_dense_points(
    *,
    points: list[qdrant_models.PointStruct],
    vector_size: int,
) -> int:
    """Upsert dense chunk points into the configured Qdrant collection."""

    ensure_qdrant_collection(vector_size=vector_size)
    client = get_qdrant_client()
    collection_name = get_settings().qdrant_collection
    try:
        client.upsert(collection_name=collection_name, points=points, wait=True)
    except Exception as exc:  # pragma: no cover - defensive wrapper for client errors
        raise VectorStoreError("Failed to upsert dense points into Qdrant.") from exc
    return len(points)
