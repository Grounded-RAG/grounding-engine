"""Pure orchestration helpers for deterministic ingestion stages."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from app.pipeline.contracts import ChunkManifest, ChunkingConfig, DocumentChunk


_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\S+")
_PARAGRAPH_BREAK_PATTERN: Final[re.Pattern[str]] = re.compile(r"\n\s*\n+")
_SENTENCE_BREAK_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+")
_HEADING_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?m)^(?:[A-Z][A-Z0-9/&,\- ]{2,}|[A-Z][A-Za-z0-9/&,\- ]{1,48}:)\s*$"
)
_BULLET_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?m)^(?:\s*[-*•]\s+|\s*\d+[\.\)]\s+)"
)


@dataclass(frozen=True)
class _ChunkSpan:
    """Absolute token and character span used while building chunk manifests."""

    start_char: int
    end_char: int
    start_token: int
    end_token: int

    @property
    def token_count(self) -> int:
        return self.end_token - self.start_token + 1


def _token_spans(text: str) -> list[tuple[int, int]]:
    """Return character spans for whitespace-delimited tokens."""

    return [(match.start(), match.end()) for match in _TOKEN_PATTERN.finditer(text)]


def _span_from_token_window(
    token_spans: list[tuple[int, int]],
    *,
    start_token: int,
    end_token: int,
) -> _ChunkSpan:
    """Build a token/character span from absolute token boundaries."""

    return _ChunkSpan(
        start_char=token_spans[start_token][0],
        end_char=token_spans[end_token][1],
        start_token=start_token,
        end_token=end_token,
    )


def _emit_chunk(
    *,
    chunks: list[DocumentChunk],
    text: str,
    document_id: UUID,
    span: _ChunkSpan,
) -> None:
    """Create one persisted chunk from an absolute token span."""

    chunk_text = re.sub(r"\s+", " ", text[span.start_char:span.end_char]).strip()
    chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:12]
    chunks.append(
        DocumentChunk(
            chunk_id=f"{document_id}:chunk:{len(chunks):04d}:{chunk_hash}",
            chunk_index=len(chunks),
            text=chunk_text,
            token_count=span.token_count,
            character_count=len(chunk_text),
            start_token=span.start_token,
            end_token=span.end_token,
        )
    )


def _build_deterministic_token_window_chunks(
    *,
    document_id: UUID,
    text: str,
    token_spans: list[tuple[int, int]],
    config: ChunkingConfig,
) -> list[DocumentChunk]:
    """Split text into deterministic overlapping token windows."""

    step = config.max_tokens - config.overlap_tokens
    chunks: list[DocumentChunk] = []
    start_token = 0

    while start_token < len(token_spans):
        end_token = min(start_token + config.max_tokens, len(token_spans)) - 1
        _emit_chunk(
            chunks=chunks,
            text=text,
            document_id=document_id,
            span=_span_from_token_window(
                token_spans,
                start_token=start_token,
                end_token=end_token,
            ),
        )

        if end_token >= len(token_spans) - 1:
            break
        start_token += step

    return chunks


def _char_spans_to_token_spans(
    text: str,
    token_spans: list[tuple[int, int]],
) -> list[_ChunkSpan]:
    """Split text into paragraph-like blocks and map them back to token spans."""

    spans: list[_ChunkSpan] = []
    block_starts = [0]
    for match in _PARAGRAPH_BREAK_PATTERN.finditer(text):
        block_starts.append(match.end())
    for match in _HEADING_LINE_PATTERN.finditer(text):
        block_starts.append(match.start())
    for match in _BULLET_LINE_PATTERN.finditer(text):
        block_starts.append(match.start())
    block_starts = sorted({start for start in block_starts if 0 <= start <= len(text)})
    if not block_starts or block_starts[-1] != len(text):
        block_starts.append(len(text))

    for start_char, end_char in zip(block_starts, block_starts[1:]):
        raw_start = start_char
        raw_end = end_char
        while raw_start < raw_end and text[raw_start].isspace():
            raw_start += 1
        while raw_end > raw_start and text[raw_end - 1].isspace():
            raw_end -= 1
        if raw_start >= raw_end:
            continue

        start_token = next(
            (
                index
                for index, (_, token_end) in enumerate(token_spans)
                if token_end > raw_start
            ),
            None,
        )
        if start_token is None:
            continue
        end_token = next(
            (
                len(token_spans) - 1 - reverse_index
                for reverse_index, (token_start, _) in enumerate(reversed(token_spans))
                if token_start < raw_end
            ),
            None,
        )
        if end_token is None or end_token < start_token:
            continue

        spans.append(
            _ChunkSpan(
                start_char=token_spans[start_token][0],
                end_char=token_spans[end_token][1],
                start_token=start_token,
                end_token=end_token,
            )
        )

    return spans


def _split_oversized_span(
    *,
    span: _ChunkSpan,
    text: str,
    token_spans: list[tuple[int, int]],
    config: ChunkingConfig,
) -> list[_ChunkSpan]:
    """Break oversized structure-aware spans at sentence boundaries when possible."""

    if span.token_count <= config.max_tokens:
        return [span]

    candidate_spans: list[_ChunkSpan] = []
    relative_start = span.start_char
    block_text = text[span.start_char:span.end_char]
    sentence_starts = [0]
    for match in _SENTENCE_BREAK_PATTERN.finditer(block_text):
        sentence_starts.append(match.end())
    sentence_starts.append(len(block_text))

    sentence_spans: list[_ChunkSpan] = []
    for start, end in zip(sentence_starts, sentence_starts[1:]):
        absolute_start = relative_start + start
        absolute_end = relative_start + end
        while absolute_start < absolute_end and text[absolute_start].isspace():
            absolute_start += 1
        while absolute_end > absolute_start and text[absolute_end - 1].isspace():
            absolute_end -= 1
        if absolute_start >= absolute_end:
            continue

        start_token = next(
            (
                index
                for index, (_, token_end) in enumerate(token_spans)
                if token_end > absolute_start
            ),
            None,
        )
        end_token = next(
            (
                len(token_spans) - 1 - reverse_index
                for reverse_index, (token_start, _) in enumerate(reversed(token_spans))
                if token_start < absolute_end
            ),
            None,
        )
        if start_token is None or end_token is None or end_token < start_token:
            continue
        sentence_spans.append(
            _ChunkSpan(
                start_char=token_spans[start_token][0],
                end_char=token_spans[end_token][1],
                start_token=start_token,
                end_token=end_token,
            )
        )

    if len(sentence_spans) <= 1:
        return [
            _span_from_token_window(
                token_spans,
                start_token=start_token,
                end_token=min(start_token + config.max_tokens - 1, span.end_token),
            )
            for start_token in range(
                span.start_token,
                span.end_token + 1,
                max(config.max_tokens - config.overlap_tokens, 1),
            )
        ]

    current = sentence_spans[0]
    for sentence_span in sentence_spans[1:]:
        merged_end_token = sentence_span.end_token
        merged_start_token = current.start_token
        merged_token_count = merged_end_token - merged_start_token + 1
        if merged_token_count <= config.max_tokens:
            current = _ChunkSpan(
                start_char=current.start_char,
                end_char=sentence_span.end_char,
                start_token=current.start_token,
                end_token=sentence_span.end_token,
            )
            continue

        candidate_spans.append(current)
        current = sentence_span
    candidate_spans.append(current)

    return candidate_spans


def _apply_overlap(
    *,
    base_spans: list[_ChunkSpan],
    token_spans: list[tuple[int, int]],
    overlap_tokens: int,
) -> list[_ChunkSpan]:
    """Extend structure-aware chunks backwards to preserve local overlap."""

    if overlap_tokens <= 0 or not base_spans:
        return base_spans

    overlapped: list[_ChunkSpan] = []
    for index, span in enumerate(base_spans):
        if index == 0:
            overlapped.append(span)
            continue
        start_token = max(0, span.start_token - overlap_tokens)
        overlapped.append(
            _ChunkSpan(
                start_char=token_spans[start_token][0],
                end_char=span.end_char,
                start_token=start_token,
                end_token=span.end_token,
            )
        )
    return overlapped


def _build_structure_aware_chunks(
    *,
    document_id: UUID,
    text: str,
    token_spans: list[tuple[int, int]],
    config: ChunkingConfig,
) -> list[DocumentChunk]:
    """Preserve paragraph/sentence boundaries before falling back to token windows."""

    raw_spans = _char_spans_to_token_spans(text, token_spans)
    normalized_spans: list[_ChunkSpan] = []
    for span in raw_spans:
        normalized_spans.extend(
            _split_oversized_span(
                span=span,
                text=text,
                token_spans=token_spans,
                config=config,
            )
        )

    if not normalized_spans:
        return _build_deterministic_token_window_chunks(
            document_id=document_id,
            text=text,
            token_spans=token_spans,
            config=config,
        )

    grouped_spans: list[_ChunkSpan] = []
    current = normalized_spans[0]
    for span in normalized_spans[1:]:
        merged_token_count = span.end_token - current.start_token + 1
        if merged_token_count <= config.max_tokens:
            current = _ChunkSpan(
                start_char=current.start_char,
                end_char=span.end_char,
                start_token=current.start_token,
                end_token=span.end_token,
            )
            continue

        grouped_spans.append(current)
        current = span
    grouped_spans.append(current)

    chunks: list[DocumentChunk] = []
    for span in _apply_overlap(
        base_spans=grouped_spans,
        token_spans=token_spans,
        overlap_tokens=config.overlap_tokens,
    ):
        _emit_chunk(
            chunks=chunks,
            text=text,
            document_id=document_id,
            span=span,
        )
    return chunks


def build_chunk_manifest(
    *,
    document_id: UUID,
    text: str,
    source_artifact_key: str,
    config: ChunkingConfig,
) -> ChunkManifest:
    """Split normalized text into a stable chunk manifest for indexing."""

    token_spans = _token_spans(text)
    if not token_spans:
        return ChunkManifest(
            document_id=document_id,
            source_artifact_key=source_artifact_key,
            chunking_strategy=config.strategy,
            chunks=[],
        )

    if config.strategy == "structure_aware_v1":
        chunks = _build_structure_aware_chunks(
            document_id=document_id,
            text=text,
            token_spans=token_spans,
            config=config,
        )
    else:
        chunks = _build_deterministic_token_window_chunks(
            document_id=document_id,
            text=text,
            token_spans=token_spans,
            config=config,
        )

    return ChunkManifest(
        document_id=document_id,
        source_artifact_key=source_artifact_key,
        chunking_strategy=config.strategy,
        chunks=chunks,
    )
