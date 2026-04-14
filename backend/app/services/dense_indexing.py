"""Dense indexing helpers for chunk manifests."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from qdrant_client.http import models as qdrant_models

from app.config import get_settings
from app.core.embeddings import DenseEmbedding, EmbeddingError, embed_texts
from app.core.qdrant_client import (
    VectorStoreError,
    delete_dense_points_for_document,
    upsert_dense_points,
)
from app.core.storage import StorageError, download_bytes
from app.pipeline.contracts import ChunkManifest
from app.services.chunking import derive_chunk_manifest_key
from app.services.ingestion import IngestionJobContext, IngestionProcessorError


@dataclass(frozen=True)
class DenseIndexingResult:
    """Dense indexing output for a persisted chunk manifest."""

    collection_name: str
    points_indexed: int
    vector_dimensions: int
    manifest_key: str


def _dense_point_id(chunk_id: str) -> str:
    """Derive a deterministic Qdrant-compatible UUID from one chunk id."""

    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def _build_dense_point(
    *,
    context: IngestionJobContext,
    manifest: ChunkManifest,
    embedding: DenseEmbedding,
    chunk_index: int,
) -> qdrant_models.PointStruct:
    """Build one Qdrant point for a chunk embedding."""

    chunk = manifest.chunks[chunk_index]
    return qdrant_models.PointStruct(
        id=_dense_point_id(chunk.chunk_id),
        vector=embedding.vector,
        payload={
            "tenant_id": str(context.tenant_id),
            "namespace_id": str(context.namespace_id),
            "document_id": str(context.document_id),
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "section_title": chunk.section_title,
            "section_slug": chunk.section_slug,
            "chunk_role": chunk.chunk_role,
            "starts_with_heading": chunk.starts_with_heading,
            "is_list_block": chunk.is_list_block,
            "mime_type": context.mime_type,
            "title": context.title,
            "token_count": chunk.token_count,
            "character_count": chunk.character_count,
            "start_token": chunk.start_token,
            "end_token": chunk.end_token,
            "source_artifact_key": manifest.source_artifact_key,
            "chunking_strategy": manifest.chunking_strategy,
        },
    )


async def dense_index_document(
    context: IngestionJobContext,
) -> DenseIndexingResult:
    """Read a chunk manifest, embed its chunks, and upsert them into Qdrant."""

    manifest_key = derive_chunk_manifest_key(context.object_key)
    try:
        manifest_bytes = await download_bytes(manifest_key)
    except StorageError as exc:
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_NOT_FOUND",
            "Chunk manifest artifact is missing for dense indexing.",
        ) from exc

    try:
        manifest_payload = json.loads(manifest_bytes.decode("utf-8"))
        manifest = ChunkManifest.from_payload(manifest_payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_INVALID",
            "Chunk manifest artifact could not be parsed for dense indexing.",
        ) from exc

    if not manifest.chunks:
        raise IngestionProcessorError(
            "EMPTY_CHUNK_MANIFEST",
            "Dense indexing requires at least one chunk in the manifest.",
        )

    try:
        embeddings = await embed_texts(
            [chunk.text for chunk in manifest.chunks],
            purpose="document",
        )
    except EmbeddingError as exc:
        raise IngestionProcessorError(
            "DENSE_EMBEDDING_FAILED",
            "Dense indexing could not generate embeddings for chunk text.",
        ) from exc

    vector_dimensions = get_settings().dense_embedding_dimensions
    points = [
        _build_dense_point(
            context=context,
            manifest=manifest,
            embedding=embedding,
            chunk_index=chunk_index,
        )
        for chunk_index, embedding in enumerate(embeddings)
    ]

    try:
        delete_dense_points_for_document(
            tenant_id=context.tenant_id,
            document_id=context.document_id,
        )
        points_indexed = upsert_dense_points(
            points=points,
            vector_size=vector_dimensions,
        )
    except VectorStoreError as exc:
        raise IngestionProcessorError(
            "DENSE_INDEX_UPSERT_FAILED",
            "Dense indexing failed while writing chunk vectors to Qdrant.",
        ) from exc

    return DenseIndexingResult(
        collection_name=get_settings().qdrant_collection,
        points_indexed=points_indexed,
        vector_dimensions=vector_dimensions,
        manifest_key=manifest_key,
    )
