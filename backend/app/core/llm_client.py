"""Grounded generation client helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft


class GroundedGenerationError(RuntimeError):
    """Raised when grounded generation cannot produce a usable draft."""


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+|[•·]+|(?<=;)\s+")
_STOPWORDS = {
    "about",
    "does",
    "give",
    "have",
    "hello",
    "help",
    "into",
    "just",
    "need",
    "please",
    "show",
    "tell",
    "their",
    "them",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "your",
}


def _normalize_term(token: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", token.casefold())
    if normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized


def _tokenize_query(query_text: str) -> set[str]:
    """Return normalized query tokens for simple lexical overlap scoring."""

    return {
        normalized
        for token in re.findall(r"[A-Za-z0-9]+", query_text)
        if (normalized := _normalize_term(token)) and len(normalized) >= 3 and normalized not in _STOPWORDS
    }


def _sentence_candidates(text: str) -> list[str]:
    """Split evidence text into compact sentence candidates."""

    candidates = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_PATTERN.split(text)
        if sentence.strip()
    ]
    return candidates or [text.strip()]


def _sentence_terms(text: str) -> set[str]:
    return {
        normalized
        for token in re.findall(r"[A-Za-z0-9]+", text)
        if (normalized := _normalize_term(token)) and len(normalized) >= 3
    }


def _term_matches_sentence(term: str, sentence_terms: set[str]) -> bool:
    if term in sentence_terms:
        return True
    return any(SequenceMatcher(a=term, b=candidate).ratio() >= 0.86 for candidate in sentence_terms)


def _select_grounded_snippet(
    item: EvidenceItem,
    *,
    query_terms: set[str],
) -> tuple[str, int, float]:
    """Select the most query-aligned sentence from one evidence item."""

    best_sentence = ""
    best_overlap = 0
    best_score = -1
    for sentence in _sentence_candidates(item.text):
        sentence_terms = _sentence_terms(sentence)
        overlap = sum(1 for term in query_terms if _term_matches_sentence(term, sentence_terms))
        length_bonus = min(len(sentence), 160) / 160
        coverage_bonus = overlap / max(len(query_terms), 1)
        score = overlap * 10 + coverage_bonus * 4 + length_bonus
        if score > best_score:
            best_sentence = sentence
            best_overlap = overlap
            best_score = score
    return best_sentence or item.text.strip(), best_overlap, best_score


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
    if not query_terms:
        raise GroundedGenerationError(
            "Grounded generation requires meaningful query terms."
        )

    rendered_parts: list[str] = []
    cited_ids: list[str] = []
    citation_snippets: dict[str, str] = {}
    ranked_support: list[tuple[float, EvidenceItem, str]] = []

    for item in evidence_package.items:
        snippet, overlap, score = _select_grounded_snippet(item, query_terms=query_terms)
        if not snippet or overlap <= 0:
            continue

        ranked_support.append((score, item, snippet))

    if not ranked_support:
        raise GroundedGenerationError(
            "Grounded generation could not derive query-aligned support."
        )

    for _, item, snippet in sorted(ranked_support, key=lambda entry: entry[0], reverse=True)[:3]:
        rendered_parts.append(f"{snippet} [{item.citation_id}]")
        cited_ids.append(item.chunk_id)
        citation_snippets[item.chunk_id] = snippet

    if not rendered_parts:
        raise GroundedGenerationError(
            "Grounded generation could not derive any supported answer content."
        )

    answer_text = " ".join(rendered_parts)
    return GroundedAnswerDraft(
        answer_text=answer_text,
        cited_evidence_ids=cited_ids,
        citation_snippets=citation_snippets,
        generator_provider="local-grounded-v1",
    )
