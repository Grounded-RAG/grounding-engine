"""Pure orchestration helpers for deterministic ingestion stages."""

from __future__ import annotations

import hashlib
import re
from typing import Final
from uuid import UUID

from app.pipeline.contracts import ChunkManifest, ChunkingConfig, DocumentChunk


_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\S+")


def _token_spans(text: str) -> list[tuple[int, int]]:
    """Return character spans for whitespace-delimited tokens."""

    return [(match.start(), match.end()) for match in _TOKEN_PATTERN.finditer(text)]


def build_chunk_manifest(
    *,
    document_id: UUID,
    text: str,
    source_artifact_key: str,
    config: ChunkingConfig,
) -> ChunkManifest:
    """Split normalized text into deterministic overlapping token windows."""

    spans = _token_spans(text)
    if not spans:
        return ChunkManifest(
            document_id=document_id,
            source_artifact_key=source_artifact_key,
            chunking_strategy="deterministic_token_window_v1",
            chunks=[],
        )

    step = config.max_tokens - config.overlap_tokens
    chunks: list[DocumentChunk] = []
    start_token = 0
    chunk_index = 0

    while start_token < len(spans):
        end_token = min(start_token + config.max_tokens, len(spans))
        start_char = spans[start_token][0]
        end_char = spans[end_token - 1][1]
        chunk_text = text[start_char:end_char].strip()
        token_count = end_token - start_token
        chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:12]
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document_id}:chunk:{chunk_index:04d}:{chunk_hash}",
                chunk_index=chunk_index,
                text=chunk_text,
                token_count=token_count,
                character_count=len(chunk_text),
                start_token=start_token,
                end_token=end_token - 1,
            )
        )

        if end_token >= len(spans):
            break
        start_token += step
        chunk_index += 1

    return ChunkManifest(
        document_id=document_id,
        source_artifact_key=source_artifact_key,
        chunking_strategy="deterministic_token_window_v1",
        chunks=chunks,
    )
