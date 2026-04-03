"""Deterministic chunking helpers for extracted documents."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import get_settings
from app.core.storage import StorageError, download_bytes, upload_bytes
from app.pipeline.contracts import ChunkManifest, ChunkingConfig
from app.pipeline.orchestrator import build_chunk_manifest
from app.services.extraction import derive_extracted_text_key
from app.services.ingestion import IngestionJobContext, IngestionProcessorError


@dataclass(frozen=True)
class ChunkedDocumentArtifact:
    """Chunk manifest persisted for later dense and sparse indexing."""

    manifest_key: str
    manifest: ChunkManifest
    chunk_count: int


def derive_chunk_manifest_key(object_key: str) -> str:
    """Derive the storage key used for a persisted chunk manifest."""

    if "/source/" in object_key:
        prefix, _ = object_key.split("/source/", maxsplit=1)
        return f"{prefix}/artifacts/chunks/manifest.json"
    return f"{object_key}.chunks.json"


async def chunk_extracted_document(
    context: IngestionJobContext,
) -> ChunkedDocumentArtifact:
    """Read normalized extracted text, chunk it deterministically, and persist a manifest."""

    extracted_text_key = derive_extracted_text_key(context.object_key)
    try:
        extracted_bytes = await download_bytes(extracted_text_key)
    except StorageError as exc:
        raise IngestionProcessorError(
            "EXTRACTED_TEXT_NOT_FOUND",
            "Normalized extracted text artifact is missing for chunking.",
        ) from exc

    try:
        text = extracted_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestionProcessorError(
            "EXTRACTED_TEXT_DECODE_FAILED",
            "Chunking could not decode the normalized extracted text artifact.",
        ) from exc

    settings = get_settings()
    manifest = build_chunk_manifest(
        document_id=context.document_id,
        text=text,
        source_artifact_key=extracted_text_key,
        config=ChunkingConfig(
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            strategy=settings.chunking_strategy,
        ),
    )
    if not manifest.chunks:
        raise IngestionProcessorError(
            "EMPTY_CHUNK_MANIFEST",
            "Chunking produced no chunks from the extracted document text.",
        )

    manifest_key = derive_chunk_manifest_key(context.object_key)
    try:
        await upload_bytes(
            manifest_key,
            json.dumps(manifest.to_payload(), ensure_ascii=True).encode("utf-8"),
            content_type="application/json",
            metadata={
                "tenant_id": str(context.tenant_id),
                "document_id": str(context.document_id),
                "chunk_count": str(len(manifest.chunks)),
                "source_artifact_key": extracted_text_key,
            },
        )
    except StorageError as exc:
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_UPLOAD_FAILED",
            "Failed to store the chunk manifest artifact.",
        ) from exc

    return ChunkedDocumentArtifact(
        manifest_key=manifest_key,
        manifest=manifest,
        chunk_count=len(manifest.chunks),
    )
