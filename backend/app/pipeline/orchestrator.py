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
    r"(?m)^(?:\s*[-*\u2022\u2013\u2014]\s+|\s*\d+[\.\)]\s+)"
)
_KEY_VALUE_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z][A-Za-z0-9/&()' -]{0,40}:\s+\S"
)
_TABLE_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:\||\t|(?:\S+\s{2,}\S+\s{2,}\S+))"
)


@dataclass(frozen=True)
class _ChunkSpan:
    """Absolute token and character span used while building chunk manifests."""

    start_char: int
    end_char: int
    start_token: int
    end_token: int
    starts_with_heading: bool = False

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


def _normalize_chunk_text(raw_text: str) -> str:
    """Normalize chunk text while preserving meaningful line structure."""

    normalized_source = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = normalized_source.split("\n")

    normalized_lines = [
        _normalize_display_line(line)
        for line in raw_lines
    ]
    paired_lines = _pair_label_value_lines(normalized_lines)
    compact_lines: list[str] = []
    previous_blank = False
    for line in paired_lines:
        if not line:
            if compact_lines and not previous_blank:
                compact_lines.append("")
            previous_blank = True
            continue
        if compact_lines and _should_merge_with_previous_line(compact_lines[-1], line):
            compact_lines[-1] = f"{compact_lines[-1].rstrip()} {line.lstrip()}".strip()
        else:
            compact_lines.append(line)
        previous_blank = False

    return "\n".join(compact_lines).strip()


def _starts_with_heading(text: str, *, start_char: int, end_char: int) -> bool:
    """Return whether a span begins with a heading-like line."""

    candidate = text[start_char:end_char].lstrip()
    if not candidate:
        return False
    first_line = candidate.splitlines()[0].strip()
    return bool(first_line and _HEADING_LINE_PATTERN.fullmatch(first_line))


def _normalize_display_line(raw_line: str) -> str:
    """Normalize one line while preserving table-like separators when present."""

    stripped = raw_line.strip()
    if not stripped:
        return ""
    if _TABLE_LINE_PATTERN.search(raw_line):
        table_like = re.sub(r"\t+", " | ", stripped)
        table_like = re.sub(r"\s{2,}", " | ", table_like)
        return re.sub(r"\s+", " ", table_like).strip()
    return re.sub(r"[ \t]+", " ", stripped).strip()


def _looks_like_table_line(line: str) -> bool:
    """Return whether a normalized line still looks table-like."""

    stripped = line.strip()
    if not stripped:
        return False
    return "|" in stripped


def _looks_like_key_value_line(line: str) -> bool:
    """Return whether one normalized line looks like a short key-value row."""

    stripped = line.strip()
    return bool(stripped and _KEY_VALUE_LINE_PATTERN.fullmatch(stripped))


def _looks_like_label_only_line(line: str) -> bool:
    """Return whether a short line likely represents a form label awaiting a value."""

    stripped = line.strip().rstrip(":")
    if (
        not stripped
        or _HEADING_LINE_PATTERN.fullmatch(stripped)
        or _BULLET_LINE_PATTERN.match(stripped)
        or _looks_like_table_line(stripped)
        or _looks_like_key_value_line(stripped)
        or any(character.isdigit() for character in stripped)
        or len(stripped.split()) > 5
    ):
        return False
    return stripped == stripped.title() or stripped.isupper()


def _pair_label_value_lines(lines: list[str]) -> list[str]:
    """Combine short form-style label/value rows into single key-value lines."""

    paired: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            paired.append("")
            index += 1
            continue

        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if (
            _looks_like_label_only_line(line)
            and next_line
            and not _looks_like_label_only_line(next_line)
            and not _HEADING_LINE_PATTERN.fullmatch(next_line)
            and not _BULLET_LINE_PATTERN.match(next_line)
            and not _looks_like_table_line(next_line)
        ):
            paired.append(f"{line.rstrip(':')}: {next_line}")
            index += 2
            continue

        paired.append(line)
        index += 1

    return paired


def _should_merge_with_previous_line(previous_line: str, current_line: str) -> bool:
    """Return whether one line is a continuation of the previous structured line."""

    previous = previous_line.strip()
    current = current_line.strip()
    if (
        not previous
        or not current
        or _HEADING_LINE_PATTERN.fullmatch(current)
        or _BULLET_LINE_PATTERN.match(current)
        or _looks_like_table_line(previous)
        or _looks_like_table_line(current)
        or _looks_like_label_only_line(current)
        or _looks_like_key_value_line(current)
    ):
        return False

    if previous.endswith((":", ";", ",", "/")):
        return True

    if _BULLET_LINE_PATTERN.match(previous) or _looks_like_key_value_line(previous):
        return True

    if re.search(r"[.!?]$", previous):
        return False

    first_character = current[0]
    if first_character.islower() or first_character.isdigit():
        return True

    return not _looks_like_label_only_line(previous)


def _leading_heading_title(text: str) -> str | None:
    """Extract a normalized leading heading title when one exists."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    first_line = lines[0]
    if not _HEADING_LINE_PATTERN.fullmatch(first_line):
        return None
    return re.sub(r"\s+", " ", first_line.rstrip(":")).strip() or None


def _slugify_section_title(section_title: str) -> str:
    """Create a stable slug for one section title."""

    slug = re.sub(r"[^a-z0-9]+", "-", section_title.casefold()).strip("-")
    return slug or "section"


def _looks_like_list_block(text: str) -> bool:
    """Return whether a chunk looks like a list/category block."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    bullet_lines = len(
        [
            line
            for line in text.splitlines()
            if _BULLET_LINE_PATTERN.match(line)
        ]
    )
    colon_lines = len([line for line in lines if ":" in line])
    key_value_lines = len([line for line in lines if _looks_like_key_value_line(line)])
    table_lines = len([line for line in lines if _looks_like_table_line(line)])
    short_lines = len([line for line in lines if len(line.split()) <= 10])
    if bullet_lines >= 1 or colon_lines >= 2 or key_value_lines >= 2 or table_lines >= 2:
        return True
    return len(lines) >= 3 and short_lines >= 2


def _chunk_role_for_metadata(
    *,
    chunk_index: int,
    section_title: str | None,
    starts_with_heading: bool,
    is_list_block: bool,
) -> str:
    """Classify one chunk into a lightweight structural role."""

    if section_title:
        if starts_with_heading:
            return "section_header"
        if is_list_block:
            return "section_list"
        return "section_body"
    if chunk_index == 0:
        return "document_header"
    if is_list_block:
        return "list"
    return "body"


def _emit_chunk(
    *,
    chunks: list[DocumentChunk],
    text: str,
    document_id: UUID,
    span: _ChunkSpan,
    section_title: str | None = None,
    section_slug: str | None = None,
) -> None:
    """Create one persisted chunk from an absolute token span."""

    chunk_text = _normalize_chunk_text(text[span.start_char:span.end_char])
    leading_heading_title = _leading_heading_title(chunk_text)
    effective_section_title = leading_heading_title or section_title
    effective_section_slug = (
        _slugify_section_title(effective_section_title)
        if effective_section_title
        else section_slug
    )
    is_list_block = _looks_like_list_block(chunk_text)
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
            section_title=effective_section_title,
            section_slug=effective_section_slug,
            chunk_role=_chunk_role_for_metadata(
                chunk_index=len(chunks),
                section_title=effective_section_title,
                starts_with_heading=span.starts_with_heading,
                is_list_block=is_list_block,
            ),
            starts_with_heading=span.starts_with_heading,
            is_list_block=is_list_block,
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
    cursor = 0
    for raw_line in text.splitlines(keepends=True):
        normalized_line = _normalize_display_line(raw_line)
        if normalized_line and (
            _looks_like_key_value_line(normalized_line)
            or _looks_like_table_line(normalized_line)
        ):
            block_starts.append(cursor)
        cursor += len(raw_line)
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
                starts_with_heading=_starts_with_heading(
                    text,
                    start_char=raw_start,
                    end_char=raw_end,
                ),
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
                starts_with_heading=(
                    span.starts_with_heading and absolute_start == span.start_char
                ),
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
                starts_with_heading=current.starts_with_heading,
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
        if index == 0 or span.starts_with_heading:
            overlapped.append(span)
            continue
        start_token = max(0, span.start_token - overlap_tokens)
        overlapped.append(
            _ChunkSpan(
                start_char=token_spans[start_token][0],
                end_char=span.end_char,
                start_token=start_token,
                end_token=span.end_token,
                starts_with_heading=False,
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
        if span.starts_with_heading:
            grouped_spans.append(current)
            current = span
            continue
        merged_token_count = span.end_token - current.start_token + 1
        if merged_token_count <= config.max_tokens:
            current = _ChunkSpan(
                start_char=current.start_char,
                end_char=span.end_char,
                start_token=current.start_token,
                end_token=span.end_token,
                starts_with_heading=current.starts_with_heading,
            )
            continue

        grouped_spans.append(current)
        current = span
    grouped_spans.append(current)

    chunks: list[DocumentChunk] = []
    current_section_title: str | None = None
    current_section_slug: str | None = None
    for span in _apply_overlap(
        base_spans=grouped_spans,
        token_spans=token_spans,
        overlap_tokens=config.overlap_tokens,
    ):
        span_text = _normalize_chunk_text(text[span.start_char:span.end_char])
        detected_section_title = _leading_heading_title(span_text)
        if detected_section_title:
            current_section_title = detected_section_title
            current_section_slug = _slugify_section_title(detected_section_title)
        _emit_chunk(
            chunks=chunks,
            text=text,
            document_id=document_id,
            span=span,
            section_title=current_section_title,
            section_slug=current_section_slug,
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
