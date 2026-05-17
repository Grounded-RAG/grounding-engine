"""Sparse indexing helpers for chunk manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import delete, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageError, download_bytes
from app.models import DocumentChunkRecord
from app.pipeline.contracts import ChunkManifest
from app.services.chunking import derive_chunk_manifest_key
from app.services.ingestion import IngestionJobContext, IngestionProcessorError


@dataclass(frozen=True)
class SparseIndexingResult:
    """Sparse indexing output for a persisted chunk manifest."""

    rows_indexed: int
    manifest_key: str


def _build_chunk_rows(
    *,
    context: IngestionJobContext,
    manifest: ChunkManifest,
) -> list[dict[str, object]]:
    """Translate a chunk manifest into document chunk table rows."""

    return [
        {
            "chunk_id": chunk.chunk_id,
            "tenant_id": context.tenant_id,
            "namespace_id": context.namespace_id,
            "doc_id": context.document_id,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.text,
            "section_title": chunk.section_title,
            "section_slug": chunk.section_slug,
            "chunk_role": chunk.chunk_role,
            "starts_with_heading": chunk.starts_with_heading,
            "is_list_block": chunk.is_list_block,
            "token_count": chunk.token_count,
            "character_count": chunk.character_count,
            "start_token": chunk.start_token,
            "end_token": chunk.end_token,
        }
        for chunk in manifest.chunks
    ]


async def sparse_index_document(
    *,
    session: AsyncSession,
    context: IngestionJobContext,
) -> SparseIndexingResult:
    """Read a chunk manifest and materialize it into PostgreSQL chunk rows."""

    manifest_key = derive_chunk_manifest_key(context.object_key)
    try:
        manifest_bytes = await download_bytes(manifest_key)
    except StorageError as exc:
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_NOT_FOUND",
            "Chunk manifest artifact is missing for sparse indexing.",
        ) from exc

    try:
        manifest_payload = json.loads(manifest_bytes.decode("utf-8"))
        manifest = ChunkManifest.from_payload(manifest_payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_INVALID",
            "Chunk manifest artifact could not be parsed for sparse indexing.",
        ) from exc

    if not manifest.chunks:
        raise IngestionProcessorError(
            "EMPTY_CHUNK_MANIFEST",
            "Sparse indexing requires at least one chunk in the manifest.",
        )

    rows = _build_chunk_rows(context=context, manifest=manifest)

    try:
        await session.execute(
            delete(DocumentChunkRecord).where(
                DocumentChunkRecord.tenant_id == context.tenant_id,
                DocumentChunkRecord.doc_id == context.document_id,
            )
        )
        await session.execute(insert(DocumentChunkRecord), rows)
        await session.flush()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise IngestionProcessorError(
            "SPARSE_INDEX_WRITE_FAILED",
            "Sparse indexing failed while writing chunk rows to PostgreSQL.",
        ) from exc

    return SparseIndexingResult(
        rows_indexed=len(rows),
        manifest_key=manifest_key,
    )
