"""Grounded generation client helpers."""

from __future__ import annotations

import re

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft


class GroundedGenerationError(RuntimeError):
    """Raised when grounded generation cannot produce a usable draft."""


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")


def _tokenize_query(query_text: str) -> set[str]:
    """Return normalized query tokens for simple lexical overlap scoring."""

    return {
        token
        for token in re.findall(r"[A-Za-z0-9]+", query_text.casefold())
        if len(token) >= 3
    }


def _sentence_candidates(text: str) -> list[str]:
    """Split evidence text into compact sentence candidates."""

    candidates = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_PATTERN.split(text)
        if sentence.strip()
    ]
    return candidates or [text.strip()]


def _select_grounded_snippet(item: EvidenceItem, *, query_terms: set[str]) -> str:
    """Select the most query-aligned sentence from one evidence item."""

    best_sentence = ""
    best_score = -1
    for sentence in _sentence_candidates(item.text):
        lowered = sentence.casefold()
        overlap = sum(1 for term in query_terms if term in lowered)
        length_bonus = min(len(sentence), 160) / 160
        score = overlap * 10 + length_bonus
        if score > best_score:
            best_sentence = sentence
            best_score = score
    return best_sentence or item.text.strip()


def generate_grounded_draft(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a deterministic grounded answer draft from packaged evidence."""

    if not evidence_package.items:
        raise GroundedGenerationError(
            "Grounded generation requires at least one evidence item."
        )

    query_terms = _tokenize_query(query_text)
    rendered_parts: list[str] = []
    cited_ids: list[str] = []

    for item in evidence_package.items:
        snippet = _select_grounded_snippet(item, query_terms=query_terms)
        if not snippet:
            continue
        rendered_parts.append(f"{snippet} [{item.citation_id}]")
        cited_ids.append(item.chunk_id)

    if not rendered_parts:
        raise GroundedGenerationError(
            "Grounded generation could not derive any supported answer content."
        )

    answer_text = " ".join(rendered_parts)
    return GroundedAnswerDraft(
        answer_text=answer_text,
        cited_evidence_ids=cited_ids,
        generator_provider="local-grounded-v1",
    )
