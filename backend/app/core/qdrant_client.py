"""Qdrant client helpers for dense chunk indexing."""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import get_settings


class VectorStoreError(RuntimeError):
    """Raised when dense vector storage operations fail."""


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Return a cached Qdrant client using the configured endpoint."""

    settings = get_settings()
    return QdrantClient(
        url=str(settings.qdrant_url),
        check_compatibility=settings.qdrant_check_compatibility,
    )


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


def delete_dense_points_for_document(
    *,
    tenant_id: UUID,
    document_id: UUID,
) -> None:
    """Delete all dense points currently stored for one tenant-scoped document."""

    client = get_qdrant_client()
    collection_name = get_settings().qdrant_collection
    query_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="tenant_id",
                match=qdrant_models.MatchValue(value=str(tenant_id)),
            ),
            qdrant_models.FieldCondition(
                key="document_id",
                match=qdrant_models.MatchValue(value=str(document_id)),
            ),
        ]
    )
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(filter=query_filter),
            wait=True,
        )
    except Exception as exc:  # pragma: no cover - defensive wrapper for client errors
        raise VectorStoreError(
            "Failed to delete existing dense points for the document."
        ) from exc


def search_dense_points(
    *,
    query_vector: list[float],
    tenant_id: UUID,
    namespace_id: UUID,
    limit: int,
) -> list[qdrant_models.ScoredPoint]:
    """Search dense chunk vectors scoped to one tenant namespace."""

    client = get_qdrant_client()
    collection_name = get_settings().qdrant_collection
    query_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="tenant_id",
                match=qdrant_models.MatchValue(value=str(tenant_id)),
            ),
            qdrant_models.FieldCondition(
                key="namespace_id",
                match=qdrant_models.MatchValue(value=str(namespace_id)),
            ),
        ]
    )
    try:
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return list(response.points)
    except Exception as exc:  # pragma: no cover - defensive wrapper for client errors
        raise VectorStoreError("Failed to search dense points in Qdrant.") from exc
