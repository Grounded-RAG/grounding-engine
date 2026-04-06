"""Grounded generation client helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.core.query_analysis import (
    QueryProfile,
    build_query_profile,
    has_strong_intent_signal,
    is_boolean_query,
    is_definition_query,
    is_field_extraction_query,
    primary_intent,
    query_focus_hints,
    score_text_against_query,
    tokenize_meaningful_terms,
)
from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft


class GroundedGenerationError(RuntimeError):
    """Raised when grounded generation cannot produce a usable draft."""


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+|[•·]+|(?<=;)\s+")
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
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", text)
        if len(token) >= 3
    }


def _term_matches_sentence(term: str, sentence_terms: set[str]) -> bool:
    if term in sentence_terms:
        return True
    return any(SequenceMatcher(a=term, b=candidate).ratio() >= 0.86 for candidate in sentence_terms)


def _candidate_segments(
    text: str,
    *,
    profile: QueryProfile,
) -> list[str]:
    """Return answer candidates from lines, blocks, and compact sentences."""

    candidates: list[str] = []
    lines = [line.strip(" -:\t") for line in text.splitlines() if line.strip()]
    sentence_candidates = _sentence_candidates(text)

    if len(lines) > 1:
        candidates.extend(lines)

    for index, line in enumerate(lines):
        normalized_line = line.casefold()
        if (
            any(intent.replace("_", " ") in normalized_line for intent in profile.intents)
            or normalized_line.isupper()
        ):
            candidates.append(" ".join(lines[index : index + 4]).strip())

    candidates.extend(sentence_candidates)

    if not candidates:
        candidates.append(text.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped or [text.strip()]


def _select_grounded_snippet(
    item: EvidenceItem,
    *,
    profile: QueryProfile,
) -> tuple[str, int, float]:
    """Select the most query-aligned sentence from one evidence item."""

    best_sentence = ""
    best_overlap = 0
    best_score = -1
    for sentence in _candidate_segments(item.text, profile=profile):
        sentence_terms = _sentence_terms(sentence)
        overlap = sum(1 for term in profile.terms if _term_matches_sentence(term, sentence_terms))
        length_bonus = min(len(sentence), 200) / 200
        coverage_bonus = overlap / max(len(profile.terms), 1)
        answerability_score = score_text_against_query(
            sentence,
            profile=profile,
            chunk_index=item.chunk_index,
        )
        if answerability_score <= 0 and overlap <= 0:
            continue
        compact_bonus = 1.0 if len(_sentence_candidates(sentence)) <= 1 else 0.0
        score = (
            answerability_score
            + overlap * 6
            + coverage_bonus * 3
            + length_bonus
            + compact_bonus
        )
        if score > best_score:
            best_sentence = sentence
            best_overlap = overlap
            best_score = score
    return best_sentence or item.text.strip(), best_overlap, best_score


def _definition_signal(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.casefold())
    return bool(re.search(r"\b(is|means|refers to|defined as|definition)\b", normalized))


def _clean_snippet_for_intent(snippet: str, *, profile: QueryProfile) -> str:
    """Trim one selected snippet into a concise answer-ready fragment."""

    intent = primary_intent(profile)
    lines = [
        re.sub(r"^[\s:,\-â€¢Â·]+", "", line).strip()
        for line in snippet.splitlines()
        if line.strip()
    ]
    if not lines:
        return re.sub(r"\s+", " ", snippet).strip()

    if intent in {"name", "contact"}:
        return lines[0]

    if intent == "skills":
        filtered_lines = [
            line
            for line in lines
            if line.casefold() not in {"technical skills", "skills"}
        ]
        rendered = "; ".join(filtered_lines[:5])
        return rendered or lines[0]

    if intent in {"education", "experience", "projects", "awards"}:
        return " ".join(lines[:2]).strip()

    return re.sub(r"\s+", " ", " ".join(lines[:3])).strip()


def _render_grounded_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> tuple[str, dict[str, str]]:
    """Render a concise grounded answer from the chosen support snippets."""

    cleaned_snippets: dict[str, str] = {}
    rendered_parts: list[str] = []
    for _, item, snippet in top_support:
        cleaned = _clean_snippet_for_intent(snippet, profile=profile)
        cleaned_snippets[item.chunk_id] = cleaned
        rendered_parts.append(f"{cleaned} [{item.citation_id}]")

    if is_field_extraction_query(profile) and len(rendered_parts) == 1:
        intent = primary_intent(profile)
        if intent == "name":
            return f"The person's name is {rendered_parts[0]}", cleaned_snippets
        if intent == "education":
            return f"The listed education is {rendered_parts[0]}", cleaned_snippets
        if intent == "experience":
            return f"The listed experience is {rendered_parts[0]}", cleaned_snippets
        if intent == "skills":
            return f"The listed skills are {rendered_parts[0]}", cleaned_snippets

    return " ".join(rendered_parts).strip(), cleaned_snippets


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

    profile = build_query_profile(query_text)
    if not profile.terms:
        raise GroundedGenerationError(
            "Grounded generation requires meaningful query terms."
        )

    cited_ids: list[str] = []
    citation_snippets: dict[str, str] = {}
    ranked_support: list[tuple[float, EvidenceItem, str]] = []

    for item in evidence_package.items:
        snippet, overlap, score = _select_grounded_snippet(item, profile=profile)
        if not snippet or score <= 0:
            continue

        ranked_support.append((score, item, snippet))

    if not ranked_support:
        raise GroundedGenerationError(
            "Grounded generation could not derive query-aligned support."
        )

    ranked_support = sorted(ranked_support, key=lambda entry: entry[0], reverse=True)
    if is_definition_query(profile) and not any(
        _definition_signal(snippet) for _, _, snippet in ranked_support[:2]
    ):
        raise GroundedGenerationError(
            "Grounded generation could not derive query-aligned support."
        )
    best_score = ranked_support[0][0]
    support_threshold = max(best_score * 0.6, best_score - 5.0)
    top_support: list[tuple[float, EvidenceItem, str]] = []
    covered_query_terms: set[str] = set()
    if is_field_extraction_query(profile):
        strong_support = [
            entry
            for entry in ranked_support
            if has_strong_intent_signal(entry[2], profile=profile)
            or has_strong_intent_signal(entry[1].text, profile=profile)
        ]
        if strong_support:
            ranked_support = strong_support
            best_score = ranked_support[0][0]
            support_threshold = max(best_score * 0.7, best_score - 4.0)

    for entry in ranked_support:
        score, _, snippet = entry
        snippet_terms = tokenize_meaningful_terms(snippet)
        contributes_new_terms = bool((profile.terms & snippet_terms) - covered_query_terms)
        if not top_support:
            top_support.append(entry)
            covered_query_terms.update(profile.terms & snippet_terms)
            continue
        if score >= support_threshold or (
            contributes_new_terms and score >= best_score * 0.35
        ):
            top_support.append(entry)
            covered_query_terms.update(profile.terms & snippet_terms)
        max_support_items = 1 if is_field_extraction_query(profile) and primary_intent(profile) in {
            "name",
            "contact",
            "education",
            "experience",
            "skills",
        } else 3
        if len(top_support) >= max_support_items:
            break
    if is_boolean_query(profile) and not any(
        re.search(
            r"\b(work|worked|experience|employment|role|intern|engineer|developer|manager)\b",
            snippet.casefold(),
        )
        for _, _, snippet in top_support
    ):
        raise GroundedGenerationError(
            "Grounded generation could not derive query-aligned support."
        )

    for _, item, _ in top_support:
        cited_ids.append(item.chunk_id)

    answer_text, citation_snippets = _render_grounded_answer(
        profile=profile,
        top_support=top_support,
    )

    if not answer_text:
        raise GroundedGenerationError(
            "Grounded generation could not derive any supported answer content."
        )

    focus_prefix = ""
    hints = query_focus_hints(profile)
    if hints and len(top_support) == 1 and "name" in profile.intents:
        focus_prefix = ""
    answer_text = f"{focus_prefix}{answer_text}".strip()
    support_coverage = min(len(top_support) / max(len(evidence_package.items), 1), 1.0)
    source_diversity = len({source for _, item, _ in top_support for source in item.sources})
    return GroundedAnswerDraft(
        answer_text=answer_text,
        cited_evidence_ids=cited_ids,
        citation_snippets=citation_snippets,
        generator_provider="local-grounded-v1",
        support_coverage=round(support_coverage, 4),
        source_diversity=source_diversity,
    )
