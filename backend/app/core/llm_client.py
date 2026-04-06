"""Grounded generation client helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.core.query_analysis import (
    QueryProfile,
    build_query_profile,
    has_strong_intent_signal,
    is_boolean_query,
    is_collection_query,
    is_dataset_summary_query,
    is_definition_query,
    is_field_extraction_query,
    primary_intent,
    query_focus_hints,
    requested_attribute_label,
    score_text_against_query,
    tokenize_meaningful_terms,
)
from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft


class GroundedGenerationError(RuntimeError):
    """Raised when grounded generation cannot produce a usable draft."""


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+|[\u2022\u00B7]+|(?<=;)\s+")
_HEADING_ONLY_PATTERN = re.compile(r"^[A-Z][A-Z0-9/&,\- ]{2,}$")
_SUMMARY_NAMEISH_PATTERN = re.compile(r"^[A-Z][A-Za-z'\u2019-]+(?:\s+[A-Z][A-Za-z'\u2019-]+){1,4}$")


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


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.casefold()).strip()


def _is_heading_only_line(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    return bool(stripped and _HEADING_ONLY_PATTERN.fullmatch(stripped))


def _looks_like_summary_subject_line(line: str) -> bool:
    stripped = line.strip()
    if (
        not stripped
        or stripped.isupper()
        or _is_heading_only_line(stripped)
        or any(char.isdigit() for char in stripped)
        or "@" in stripped
    ):
        return False
    return bool(_SUMMARY_NAMEISH_PATTERN.fullmatch(stripped))


def _line_matches_query_focus(line: str, *, profile: QueryProfile) -> bool:
    normalized_line = _normalize_line(line)
    if not normalized_line:
        return False
    if any(attribute in normalized_line for attribute in profile.attribute_terms):
        return True
    return any(tag in normalized_line for tag in profile.semantic_tags)


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
        candidates.extend(line for line in lines if not _is_heading_only_line(line))

    for index, line in enumerate(lines):
        if _is_heading_only_line(line) or _line_matches_query_focus(line, profile=profile):
            candidates.append("\n".join(lines[index : index + 4]).strip())
        elif is_dataset_summary_query(profile) and index == 0:
            candidates.append("\n".join(lines[:4]).strip())

    candidates.extend(sentence_candidates)

    if is_dataset_summary_query(profile) and lines:
        candidates.append("\n".join(lines[:6]).strip())

    if not candidates:
        candidates.append(text.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        stripped_candidate = candidate.strip()
        normalized = re.sub(r"\s+", " ", stripped_candidate).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(stripped_candidate)
    return deduped or [text.strip()]


def _select_grounded_snippet(
    item: EvidenceItem,
    *,
    profile: QueryProfile,
) -> tuple[str, int, float]:
    """Select the most query-aligned sentence from one evidence item."""

    best_sentence = ""
    best_overlap = 0
    best_score = -1.0
    for sentence in _candidate_segments(item.text, profile=profile):
        if _is_heading_only_line(sentence) and is_field_extraction_query(profile):
            continue
        sentence_terms = _sentence_terms(sentence)
        overlap = sum(1 for term in profile.terms if _term_matches_sentence(term, sentence_terms))
        length_bonus = min(len(sentence), 220) / 220
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
    return bool(re.search(r"\b(is|means|refers to|defined as|definition|explains?)\b", normalized))


def _clean_lines(snippet: str) -> list[str]:
    return [
        re.sub(r"^[\s:,\-*\u2022\u00B7]+", "", line).strip()
        for line in snippet.splitlines()
        if line.strip()
    ]


def _strip_attribute_prefix(line: str, *, profile: QueryProfile) -> str:
    if ":" not in line:
        return line.strip()
    prefix, suffix = [part.strip() for part in line.split(":", 1)]
    if not suffix:
        return line.strip()

    requested_label = requested_attribute_label(profile)
    normalized_prefix = _normalize_line(prefix)
    if requested_label and requested_label in normalized_prefix:
        return suffix
    if any(tag in normalized_prefix for tag in profile.semantic_tags):
        return suffix
    return line.strip()


def _format_collection_lines(lines: list[str], *, profile: QueryProfile) -> str:
    requested_label = requested_attribute_label(profile)
    filtered_lines = [
        _strip_attribute_prefix(line, profile=profile).rstrip(".")
        for line in lines
        if line
        and not _is_heading_only_line(line)
        and not (requested_label and _normalize_line(line) == requested_label)
    ]
    structured_lines = [
        line for line in filtered_lines if ":" in line or len(line.split()) <= 10
    ]
    if structured_lines:
        return "; ".join(structured_lines[:5]).strip()
    return "; ".join(filtered_lines[:3]).strip()


def _clean_snippet_for_query(snippet: str, *, profile: QueryProfile) -> str:
    """Trim one selected snippet into a concise answer-ready fragment."""

    lines = _clean_lines(snippet)
    if not lines:
        return re.sub(r"\s+", " ", snippet).strip()

    intent = primary_intent(profile)
    if intent == "name":
        return lines[0]

    if intent == "contact":
        contact_lines = [
            line
            for line in lines
            if "@" in line or re.search(r"(?:\+?\d[\d\s().-]{6,}\d)", line)
        ]
        return " ".join((contact_lines or lines)[:2]).strip()

    if is_dataset_summary_query(profile):
        if _looks_like_summary_subject_line(lines[0]):
            return lines[0]
        non_heading_lines = [line for line in lines if not _is_heading_only_line(line)]
        return " ".join(non_heading_lines[:2]).strip()

    if is_collection_query(profile):
        rendered = _format_collection_lines(lines, profile=profile)
        return rendered or " ".join(lines[:3]).strip()

    stripped_first = _strip_attribute_prefix(lines[0], profile=profile)
    if stripped_first and stripped_first != lines[0]:
        return stripped_first

    if _is_heading_only_line(lines[0]) and len(lines) > 1:
        return " ".join(lines[1:3]).strip()

    return " ".join(lines[:2]).strip()


def _format_attribute_prefix(label: str) -> str:
    return label.replace("_", " ").strip()


def _format_collection_label(label: str) -> str:
    cleaned = _format_attribute_prefix(label)
    return cleaned if cleaned.endswith("s") else f"{cleaned}s"


def _human_join(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _summary_heading_labels(text: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines()[:10]:
        line = raw_line.strip().rstrip(":")
        if not line:
            continue
        if ":" in raw_line:
            prefix = raw_line.split(":", 1)[0].strip().rstrip(":")
            if prefix and len(prefix.split()) <= 4:
                line = prefix
        if not _is_heading_only_line(line) and ":" not in raw_line:
            continue
        normalized = _normalize_line(line)
        if (
            not normalized
            or normalized in {"email", "phone", "github", "linkedin"}
            or _looks_like_summary_subject_line(line)
            or normalized in seen
        ):
            continue
        seen.add(normalized)
        labels.append(normalized)
    return labels


def _summary_subject_phrase(*, item: EvidenceItem, cleaned_snippet: str) -> str:
    lines = _clean_lines(item.text)
    if lines and _looks_like_summary_subject_line(lines[0]):
        return f"a profile for {lines[0]}"
    return cleaned_snippet.rstrip(".")


def _render_summary_answer(
    *,
    top_support: list[tuple[float, EvidenceItem, str]],
    cleaned_snippets: dict[str, str],
) -> str:
    primary_item = next(
        (
            item
            for _, item, _ in top_support
            if _looks_like_summary_subject_line(cleaned_snippets[item.chunk_id])
            or (
                _clean_lines(item.text)
                and _looks_like_summary_subject_line(_clean_lines(item.text)[0])
            )
        ),
        min((item for _, item, _ in top_support), key=lambda item: item.chunk_index),
    )
    primary_subject = _summary_subject_phrase(
        item=primary_item,
        cleaned_snippet=cleaned_snippets[primary_item.chunk_id],
    )
    sentences = [
        f"The dataset contains {primary_subject} [{primary_item.citation_id}]."
    ]

    heading_labels: list[str] = []
    heading_citation_id = primary_item.citation_id
    for _, item, _ in top_support:
        labels = _summary_heading_labels(item.text)
        if labels and not heading_labels:
            heading_citation_id = item.citation_id
        for label in labels:
            if label not in heading_labels:
                heading_labels.append(label)

    if heading_labels:
        rendered_labels = _human_join(heading_labels[:5])
        sentences.append(
            f"It includes sections on {rendered_labels} [{heading_citation_id}]."
        )
    elif len(top_support) > 1:
        secondary_item = top_support[1][1]
        secondary_summary = cleaned_snippets[secondary_item.chunk_id].rstrip(".")
        if secondary_summary:
            sentences.append(
                f"It also covers {secondary_summary} [{secondary_item.citation_id}]."
            )

    return " ".join(sentences).strip()


def _render_boolean_answer(
    *,
    top_support: list[tuple[float, EvidenceItem, str]],
    cleaned_snippets: dict[str, str],
) -> str:
    score, item, _ = top_support[0]
    del score
    cleaned = cleaned_snippets[item.chunk_id]
    normalized = cleaned.casefold()
    negative = bool(re.search(r"\b(no|not|never|without|none|did not|does not|has not|have not)\b", normalized))
    prefix = "No." if negative else "Yes."
    return f"{prefix} {cleaned} [{item.citation_id}]".strip()


def _render_grounded_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> tuple[str, dict[str, str]]:
    """Render a concise grounded answer from the chosen support snippets."""

    cleaned_snippets: dict[str, str] = {}
    rendered_parts: list[str] = []
    for _, item, snippet in top_support:
        cleaned = _clean_snippet_for_query(snippet, profile=profile)
        cleaned_snippets[item.chunk_id] = cleaned
        rendered_parts.append(f"{cleaned} [{item.citation_id}]")

    if is_boolean_query(profile):
        return _render_boolean_answer(
            top_support=top_support,
            cleaned_snippets=cleaned_snippets,
        ), cleaned_snippets

    if is_dataset_summary_query(profile):
        return _render_summary_answer(
            top_support=top_support,
            cleaned_snippets=cleaned_snippets,
        ), cleaned_snippets

    if is_field_extraction_query(profile) and len(rendered_parts) == 1:
        label = requested_attribute_label(profile)
        cleaned = cleaned_snippets[top_support[0][1].chunk_id]
        citation = top_support[0][1].citation_id
        if label:
            formatted_label = _format_attribute_prefix(label)
            if label == "name":
                return f"The person's name is {cleaned} [{citation}]".strip(), cleaned_snippets
            if label == "contact":
                return f"The contact information is {cleaned} [{citation}]".strip(), cleaned_snippets
            if is_collection_query(profile):
                return (
                    f"The listed {_format_collection_label(formatted_label)} are {cleaned} [{citation}]".strip(),
                    cleaned_snippets,
                )
            return f"The {formatted_label} is {cleaned} [{citation}]".strip(), cleaned_snippets

    return " ".join(rendered_parts).strip(), cleaned_snippets


def _field_query_support_limit(profile: QueryProfile) -> int:
    if not is_field_extraction_query(profile):
        return 3
    if is_collection_query(profile):
        return 2
    return 1


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
    support_threshold = max(best_score * 0.6, best_score - 5.0)
    top_support: list[tuple[float, EvidenceItem, str]] = []
    covered_query_terms: set[str] = set()
    max_support_items = _field_query_support_limit(profile)

    for entry in ranked_support:
        score, _, snippet = entry
        snippet_terms = tokenize_meaningful_terms(snippet)
        contributes_new_terms = bool((profile.terms & snippet_terms) - covered_query_terms)
        if not top_support:
            top_support.append(entry)
            covered_query_terms.update(profile.terms & snippet_terms)
            continue
        if score >= support_threshold or (
            contributes_new_terms
            and score >= best_score * (0.25 if not is_field_extraction_query(profile) else 0.35)
        ):
            top_support.append(entry)
            covered_query_terms.update(profile.terms & snippet_terms)
        if len(top_support) >= max_support_items:
            break

    if is_boolean_query(profile):
        strongest_overlap = max(
            len(tokenize_meaningful_terms(snippet) & set(profile.terms))
            for _, _, snippet in top_support
        )
        strongest_score = max(
            score_text_against_query(
                snippet,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            for _, item, snippet in top_support
        )
        if strongest_overlap < 2 and strongest_score < 14.0:
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

    support_coverage = min(len(top_support) / max(len(evidence_package.items), 1), 1.0)
    source_diversity = len({source for _, item, _ in top_support for source in item.sources})
    hints = query_focus_hints(profile)
    del hints  # The deterministic path already applies the hints internally.

    return GroundedAnswerDraft(
        answer_text=answer_text.strip(),
        cited_evidence_ids=cited_ids,
        citation_snippets=citation_snippets,
        generator_provider="local-grounded-v1",
        support_coverage=round(support_coverage, 4),
        source_diversity=source_diversity,
    )
