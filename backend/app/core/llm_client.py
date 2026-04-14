"""Grounded generation client helpers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from app.core.query_analysis import (
    QueryProfile,
    build_query_profile,
    has_strong_intent_signal,
    is_action_query,
    is_boolean_query,
    is_collection_query,
    is_comparison_query,
    is_count_query,
    is_dataset_summary_query,
    is_definition_query,
    is_entity_context_query,
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


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<!\d\.)(?<=[.!?])\s+|\n+|[\u2022\u00B7]+|(?<=;)\s+")
_HEADING_ONLY_PATTERN = re.compile(r"^[A-Z][A-Z0-9/&,\- ]{2,}$")
_OUTLINE_HEADING_PATTERN = re.compile(r"^\d+(?:\.\d+)*[.)]?\s+[A-Z][A-Za-z0-9/&,\- ]{2,}$")
_SUMMARY_NAMEISH_PATTERN = re.compile(r"^[A-Z][A-Za-z'\u2019-]+(?:\s+[A-Z][A-Za-z'\u2019-]+){1,4}$")
_DATE_PHRASE_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    re.IGNORECASE,
)
_ORGANIZATION_PATTERNS = (
    re.compile(r"\b(?:from|by|via|through)\s+([A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,5})"),
    re.compile(r"\b(?:supplied|provided|delivered|operated|manufactured)\s+by\s+([A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,5})", re.IGNORECASE),
)
_NUMBER_TOKEN_PATTERN = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?|[A-Za-z][A-Za-z0-9+/#&.-]*")
_NUMERIC_VALUE_PATTERN = re.compile(r"^\$?\d[\d,]*(?:\.\d+)?%?$")
_NUMBER_PHRASE_STOPWORDS = {
    "after", "and", "as", "at", "because", "before", "between", "by", "during",
    "for", "from", "if", "in", "into", "of", "on", "or", "over", "since", "than",
    "that", "through", "to", "under", "until", "via", "when", "where", "which",
    "while", "with",
}
_DATE_QUERY_TERMS = {"date", "day", "month", "start", "end", "when", "year"}
_MONEY_QUERY_TERMS = {
    "amount", "budget", "cost", "costs", "dollar", "dollars", "electricity",
    "expense", "expenses", "fee", "fees", "fuel", "price", "prices", "revenue",
    "salary", "save", "saved", "savings", "spend", "spent",
}
_MEASUREMENT_QUERY_TERMS = {
    "battery", "capacity", "distance", "hour", "hours", "kilometer", "kilometers",
    "km", "kwh", "mile", "miles", "range", "throughput",
}
_ORGANIZATION_QUERY_TERMS = {"company", "supplier", "vendor", "organization", "provider"}
_DIFFERENCE_QUERY_TERMS = {"difference", "minus", "subtract", "saved", "savings"}
_TITLE_CASE_HEADING_STOPWORDS = {
    "a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with",
}
_TITLE_CASE_HEADING_CUES = {
    "abstract",
    "achievement",
    "achievements",
    "appendix",
    "award",
    "awards",
    "background",
    "certificate",
    "certificates",
    "challenge",
    "challenges",
    "component",
    "components",
    "conclusion",
    "discussion",
    "experience",
    "feature",
    "features",
    "framework",
    "frameworks",
    "introduction",
    "method",
    "methods",
    "opportunities",
    "overview",
    "policy",
    "policies",
    "project",
    "projects",
    "requirement",
    "requirements",
    "result",
    "results",
    "section",
    "sections",
    "service",
    "services",
    "skill",
    "skills",
    "technology",
    "technologies",
    "tool",
    "tools",
    "detail",
    "details",
    "feedback",
    "finding",
    "findings",
    "operations",
    "savings",
}
_GENERIC_SECTION_LABELS = {
    "abstract",
    "acknowledgements",
    "appendix",
    "background",
    "conclusion",
    "discussion",
    "format",
    "implementation",
    "introduction",
    "limitations",
    "method",
    "methods",
    "overview",
    "practical examples and real world relevance",
    "references",
    "related work",
    "results",
    "topic selected",
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


def _looks_like_outline_heading(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    if not stripped or not _OUTLINE_HEADING_PATTERN.fullmatch(stripped):
        return False
    stripped = re.sub(r"^\d+(?:\.\d+)*[.)]?\s+", "", stripped).strip()
    words = [word for word in stripped.split() if any(char.isalpha() for char in word)]
    if not words or len(words) > 12:
        return False
    title_like_count = sum(
        1 for word in words if word[:1].isupper() or word.isupper()
    )
    return title_like_count >= max(2, len(words) - 1)


def _looks_like_title_case_heading(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    if (
        not stripped
        or stripped.endswith((".", "!", "?", ";"))
        or "@" in stripped
        or any(char.isdigit() for char in stripped)
    ):
        return False

    raw_words = stripped.split()
    if len(raw_words) < 2 or len(raw_words) > 10:
        return False

    alpha_words = [
        re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", word)
        for word in raw_words
    ]
    alpha_words = [word for word in alpha_words if word]
    if len(alpha_words) < 2:
        return False

    title_like_words = 0
    for word in alpha_words:
        normalized = word.casefold()
        if normalized in _TITLE_CASE_HEADING_STOPWORDS:
            title_like_words += 1
            continue
        if word[:1].isupper():
            title_like_words += 1

    if title_like_words < max(2, len(alpha_words) - 1):
        return False

    return any(
        word.casefold().strip("',.&/-") in _TITLE_CASE_HEADING_CUES
        for word in alpha_words
    )


def _is_heading_only_line(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    return bool(
        stripped
        and (
            _HEADING_ONLY_PATTERN.fullmatch(stripped)
            or _looks_like_outline_heading(stripped)
            or _looks_like_title_case_heading(stripped)
        )
    )


def _is_generic_section_label(line: str) -> bool:
    return _normalize_line(line).rstrip(":") in _GENERIC_SECTION_LABELS


def _looks_like_summary_subject_line(line: str) -> bool:
    stripped = line.strip()
    if (
        not stripped
        or stripped.isupper()
        or _is_heading_only_line(stripped)
        or _is_generic_section_label(stripped)
        or any(char.isdigit() for char in stripped)
        or "@" in stripped
    ):
        return False
    return bool(_SUMMARY_NAMEISH_PATTERN.fullmatch(stripped))


def _looks_like_document_title_line(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    words = stripped.split()
    if (
        not stripped
        or _is_heading_only_line(stripped)
        or _is_generic_section_label(stripped)
        or any(char.isdigit() for char in stripped)
        or "@" in stripped
        or len(words) < 3
        or len(words) > 18
    ):
        return False
    alpha_words = [word for word in words if any(character.isalpha() for character in word)]
    if len(alpha_words) < 3:
        return False
    title_like_words = [
        word
        for word in alpha_words
        if word[:1].isupper() or word.isupper()
    ]
    return len(title_like_words) >= max(2, len(alpha_words) // 2)


def _strip_reference_markers(text: str) -> str:
    cleaned = re.sub(r"\[(?:e\d{3}|\d+(?:,\s*\d+)*)\]", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,;:.")


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


def _collection_block_has_answerable_content(
    candidate: str,
    *,
    profile: QueryProfile,
) -> bool:
    lines = _clean_lines(candidate)
    non_heading_lines = [
        line for line in lines if not _is_heading_only_line(line)
    ]
    if not non_heading_lines:
        return False
    if any(
        _line_matches_query_focus(line, profile=profile)
        for line in non_heading_lines
    ):
        return True
    if any(":" in line for line in non_heading_lines):
        return True
    if len(non_heading_lines) >= 2:
        return True
    return any(len(line.split()) >= 6 for line in non_heading_lines)


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
        if (
            is_collection_query(profile)
            and "\n" in sentence
            and not _collection_block_has_answerable_content(
                sentence,
                profile=profile,
            )
        ):
            continue
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
        structured_keys = {_normalize_line(line) for line in structured_lines}
        combined_lines = list(structured_lines)
        combined_lines.extend(
            line for line in filtered_lines if _normalize_line(line) not in structured_keys
        )
        return "; ".join(combined_lines[:3]).strip()
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
        title_lines = [
            line for line in lines[:5]
            if _looks_like_document_title_line(line)
        ]
        if title_lines:
            return title_lines[0]
        if _looks_like_summary_subject_line(lines[0]):
            return lines[0]
        prose_candidates = [
            _strip_reference_markers(candidate)
            for candidate in _sentence_candidates(snippet)
            if candidate.strip()
        ]
        for candidate in prose_candidates:
            if (
                len(candidate.split()) >= 6
                and not _is_heading_only_line(candidate)
                and not _is_generic_section_label(candidate)
            ):
                return candidate
        non_heading_lines = [
            line
            for line in lines
            if not _is_heading_only_line(line) and not _is_generic_section_label(line)
        ]
        return " ".join(non_heading_lines[:2]).strip()

    if is_collection_query(profile):
        rendered = _format_collection_lines(lines, profile=profile)
        if rendered:
            return rendered
        non_heading_lines = [line for line in lines if not _is_heading_only_line(line)]
        return " ".join((non_heading_lines or lines)[:3]).strip()

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


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_line(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value.strip())
    return deduped


def _context_phrase(profile: QueryProfile) -> str | None:
    if not profile.context_terms:
        return None
    return sorted(profile.context_terms, key=len)[0].replace("_", " ").strip()


def _text_matches_context(text: str, *, profile: QueryProfile) -> bool:
    normalized_text = _normalize_line(text)
    text_terms = tokenize_meaningful_terms(text)
    for context in profile.context_terms:
        if context in normalized_text:
            return True
        if tokenize_meaningful_terms(context) & text_terms:
            return True
    return False


def _section_candidate_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in _clean_lines(text):
        normalized = _normalize_line(line)
        if (
            not normalized
            or _is_heading_only_line(line)
            or _looks_like_outline_heading(line)
            or "@" in line
            or re.search(r"\b\d{4}\b", line)
        ):
            continue
        lines.append(line)
    return _dedupe_preserving_order(lines)


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
            or _is_generic_section_label(line)
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
    for line in lines[:5]:
        if _looks_like_document_title_line(line):
            return line
    return cleaned_snippet.rstrip(".")


def _query_requests_date_range(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    return (
        ("start" in normalized and "end" in normalized)
        or ("begin" in normalized and "end" in normalized)
        or ("launch" in normalized and "end" in normalized)
    )


def _query_prefers_money(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    return any(term in normalized for term in _MONEY_QUERY_TERMS)


def _query_prefers_measurement(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    return any(term in normalized for term in _MEASUREMENT_QUERY_TERMS)


def _query_prefers_organization(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    return any(term in normalized for term in _ORGANIZATION_QUERY_TERMS)


def _query_requests_difference(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    return any(term in normalized for term in _DIFFERENCE_QUERY_TERMS)


def _extract_date_phrases(text: str) -> list[str]:
    return _dedupe_preserving_order([
        match.group(0).strip()
        for match in _DATE_PHRASE_PATTERN.finditer(text)
    ])


def _extract_numeric_phrases(text: str) -> list[str]:
    tokens = _NUMBER_TOKEN_PATTERN.findall(text)
    phrases: list[str] = []
    for index, token in enumerate(tokens):
        if not _NUMERIC_VALUE_PATTERN.fullmatch(token):
            continue
        phrase_tokens = [token]
        for next_token in tokens[index + 1 : index + 5]:
            normalized = next_token.casefold()
            if (
                _NUMERIC_VALUE_PATTERN.fullmatch(next_token)
                or normalized in _NUMBER_PHRASE_STOPWORDS
            ):
                break
            phrase_tokens.append(next_token)
        phrases.append(" ".join(phrase_tokens).rstrip("."))
    return _dedupe_preserving_order(phrases)


def _parse_decimal_value(value: str) -> Decimal | None:
    normalized = value.strip().replace(",", "")
    normalized = normalized.lstrip("$").rstrip("%")
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _format_decimal_value(
    value: Decimal,
    *,
    currency: bool = False,
    percent: bool = False,
    unit: str | None = None,
) -> str:
    if value == value.to_integral_value():
        rendered = f"{int(value):,}"
    else:
        rendered = format(value.normalize(), "f").rstrip("0").rstrip(".")
    if currency:
        rendered = f"${rendered}"
    if percent:
        rendered = f"{rendered}%"
    if unit:
        rendered = f"{rendered} {unit}".strip()
    return rendered


def _phrase_trailing_unit(phrase: str) -> str | None:
    parts = phrase.split()
    if len(parts) <= 1:
        return None
    unit = " ".join(parts[1:]).strip()
    return unit or None


def _select_best_numeric_phrase(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> tuple[str, str] | None:
    best_candidate: tuple[float, str, str] | None = None
    for _, item, _ in top_support:
        for sentence in _sentence_candidates(item.text):
            sentence_score = score_text_against_query(
                sentence,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            if sentence_score <= 0 and not any(character.isdigit() for character in sentence):
                continue
            normalized_sentence = _normalize_line(sentence)
            for phrase in _extract_numeric_phrases(sentence):
                normalized_phrase = _normalize_line(phrase)
                candidate_score = sentence_score
                if any(attribute in normalized_phrase for attribute in profile.attribute_terms):
                    candidate_score += 6.0
                if any(attribute in normalized_sentence for attribute in profile.attribute_terms):
                    candidate_score += 3.0
                if is_count_query(profile) and len(phrase.split()) > 1:
                    candidate_score += 2.0
                if _query_prefers_money(profile) and phrase.startswith("$"):
                    candidate_score += 8.0
                if _query_prefers_measurement(profile) and any(
                    unit in normalized_phrase for unit in ("kwh", "kilometer", "kilometers", "km", "mile", "miles", "hour", "hours")
                ):
                    candidate_score += 8.0
                if not _query_prefers_money(profile) and not _query_prefers_measurement(profile):
                    candidate_score += min(len(phrase.split()), 3)
                candidate = (candidate_score, phrase, item.citation_id)
                if best_candidate is None or candidate > best_candidate:
                    best_candidate = candidate
    if best_candidate is None:
        return None
    return best_candidate[1], best_candidate[2]


def _select_best_organization_phrase(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> tuple[str, str] | None:
    best_candidate: tuple[float, str, str] | None = None
    for _, item, _ in top_support:
        for sentence in _sentence_candidates(item.text):
            sentence_score = score_text_against_query(
                sentence,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            if sentence_score <= 0 and not any(character.isupper() for character in sentence):
                continue
            for pattern in _ORGANIZATION_PATTERNS:
                match = pattern.search(sentence)
                if match is None:
                    continue
                organization = match.group(1).strip().rstrip(".")
                if len(organization.split()) > 6:
                    continue
                candidate = (sentence_score + 4.0, organization, item.citation_id)
                if best_candidate is None or candidate > best_candidate:
                    best_candidate = candidate
    if best_candidate is None:
        return None
    return best_candidate[1], best_candidate[2]


def _render_date_range_answer(
    *,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str | None:
    date_candidates: list[tuple[int, str, str]] = []
    seen_dates: set[str] = set()
    for _, item, _ in sorted(
        top_support,
        key=lambda entry: (entry[1].chunk_index, entry[1].citation_id),
    ):
        for date_phrase in _extract_date_phrases(item.text):
            normalized = _normalize_line(date_phrase)
            if normalized in seen_dates:
                continue
            seen_dates.add(normalized)
            date_candidates.append((item.chunk_index, date_phrase, item.citation_id))
            if len(date_candidates) >= 3:
                break
        if len(date_candidates) >= 3:
            break
    if len(date_candidates) < 2:
        return None
    start_date = date_candidates[0]
    end_date = date_candidates[1]
    return (
        f"It started in {start_date[1]} [{start_date[2]}] "
        f"and ended in {end_date[1]} [{end_date[2]}]."
    ).strip()


def _select_best_date_phrase(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> tuple[str, str] | None:
    best_candidate: tuple[float, str, str] | None = None
    for _, item, _ in top_support:
        for sentence in _sentence_candidates(item.text):
            sentence_score = score_text_against_query(
                sentence,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            for date_phrase in _extract_date_phrases(sentence):
                candidate = (sentence_score + 5.0, date_phrase, item.citation_id)
                if best_candidate is None or candidate > best_candidate:
                    best_candidate = candidate
    if best_candidate is None:
        return None
    return best_candidate[1], best_candidate[2]


def _render_numeric_difference_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str | None:
    if not _query_requests_difference(profile):
        return None

    numeric_candidates: list[tuple[float, Decimal, str, str]] = []
    for _, item, _ in top_support:
        for sentence in _sentence_candidates(item.text):
            sentence_score = score_text_against_query(
                sentence,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            if sentence_score <= 0 and not any(character.isdigit() for character in sentence):
                continue
            for phrase in _extract_numeric_phrases(sentence):
                numeric_value = _parse_decimal_value(phrase.split()[0])
                if numeric_value is None:
                    continue
                candidate_score = sentence_score
                if phrase.startswith("$"):
                    candidate_score += 6.0
                numeric_candidates.append((candidate_score, numeric_value, phrase, item.citation_id))

    if len(numeric_candidates) < 2:
        return None

    numeric_candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    chosen: list[tuple[Decimal, str, str]] = []
    seen_values: set[Decimal] = set()
    for _, value, phrase, citation_id in numeric_candidates:
        if value in seen_values:
            continue
        seen_values.add(value)
        chosen.append((value, phrase, citation_id))
        if len(chosen) >= 2:
            break
    if len(chosen) < 2:
        return None

    first_value, first_phrase, first_citation = chosen[0]
    second_value, second_phrase, second_citation = chosen[1]
    difference = abs(first_value - second_value)
    currency = first_phrase.startswith("$") and second_phrase.startswith("$")
    unit = None
    first_unit = _phrase_trailing_unit(first_phrase)
    second_unit = _phrase_trailing_unit(second_phrase)
    if first_unit and second_unit and _normalize_line(first_unit) == _normalize_line(second_unit):
        unit = first_unit

    citation_order = {
        item.citation_id: index
        for index, (_, item, _) in enumerate(top_support)
    }
    ordered_citations = sorted(
        {first_citation, second_citation},
        key=lambda citation_id: citation_order.get(citation_id, 10_000),
    )

    rendered_difference = _format_decimal_value(
        difference,
        currency=currency,
        unit=unit,
    )
    return (
        f"The difference is {rendered_difference} "
        f"{' '.join(f'[{citation_id}]' for citation_id in ordered_citations)}."
    ).strip()


def _render_exact_field_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str | None:
    if _query_requests_date_range(profile):
        return _render_date_range_answer(top_support=top_support)

    if _query_prefers_organization(profile):
        organization = _select_best_organization_phrase(
            profile=profile,
            top_support=top_support,
        )
        if organization is not None:
            value, citation_id = organization
            return f"{value} [{citation_id}]"

    if _query_prefers_money(profile) or _query_prefers_measurement(profile):
        numeric_phrase = _select_best_numeric_phrase(
            profile=profile,
            top_support=top_support,
        )
        if numeric_phrase is not None:
            value, citation_id = numeric_phrase
            return f"{value} [{citation_id}]"

    if primary_intent(profile) == "date":
        date_phrase = _select_best_date_phrase(
            profile=profile,
            top_support=top_support,
        )
        if date_phrase is not None:
            value, citation_id = date_phrase
            return f"{value} [{citation_id}]"
    return None


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
    subject_looks_like_title = (
        _looks_like_document_title_line(primary_subject)
        and not primary_subject.casefold().startswith("a profile for ")
    )
    sentences = [
        (
            f"The dataset is about {primary_subject} [{primary_item.citation_id}]."
            if subject_looks_like_title
            else f"The dataset contains {primary_subject} [{primary_item.citation_id}]."
        )
    ]

    supporting_summary: tuple[str, str] | None = None
    for _, item, _ in top_support:
        if item.chunk_id == primary_item.chunk_id:
            continue
        candidate = cleaned_snippets[item.chunk_id].rstrip(".")
        if (
            candidate
            and candidate.casefold() != primary_subject.casefold()
            and not _is_heading_only_line(candidate)
            and not _looks_like_document_title_line(candidate)
            and len(candidate.split()) >= 6
        ):
            supporting_summary = (candidate, item.citation_id)
            break

    if supporting_summary is not None:
        supporting_text, supporting_citation_id = supporting_summary
        sentences.append(f"{supporting_text} [{supporting_citation_id}].")
    elif subject_looks_like_title:
        primary_sentences = [
            _strip_reference_markers(candidate).rstrip(".")
            for candidate in _sentence_candidates(primary_item.text)
        ]
        for candidate in primary_sentences:
            if (
                candidate
                and candidate.casefold() != primary_subject.casefold()
                and not _is_heading_only_line(candidate)
                and not _looks_like_document_title_line(candidate)
                and len(candidate.split()) >= 6
            ):
                sentences.append(f"{candidate} [{primary_item.citation_id}].")
                break

    heading_labels: list[str] = []
    heading_citation_id = primary_item.citation_id
    for _, item, _ in top_support:
        labels = _summary_heading_labels(item.text)
        if labels and not heading_labels:
            heading_citation_id = item.citation_id
        for label in labels:
            if label not in heading_labels:
                heading_labels.append(label)

    if heading_labels and supporting_summary is None:
        rendered_labels = _human_join(heading_labels[:5])
        sentences.append(
            f"It includes sections on {rendered_labels} [{heading_citation_id}]."
        )
    elif supporting_summary is None and len(top_support) > 1:
        secondary_item = top_support[1][1]
        secondary_summary = cleaned_snippets[secondary_item.chunk_id].rstrip(".")
        if secondary_summary:
            sentences.append(
                f"It also covers {secondary_summary} [{secondary_item.citation_id}]."
            )

    return " ".join(sentences).strip()


def _render_collection_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str:
    requested_label = requested_attribute_label(profile) or "items"
    rendered_lines: list[str] = []
    citations: list[str] = []

    for _, item, snippet in top_support:
        citations.append(f"[{item.citation_id}]")
        structured_lines = [
            line
            for line in _section_candidate_lines(item.text)
            if ":" in line or len(line.split()) <= 12
        ]
        prose_candidates = sorted(
            (
                (
                    score_text_against_query(
                        sentence,
                        profile=profile,
                        chunk_index=item.chunk_index,
                    ),
                    _strip_reference_markers(sentence).rstrip("."),
                )
                for sentence in _sentence_candidates(item.text)
                if not _is_heading_only_line(sentence)
            ),
            key=lambda entry: (-entry[0], len(entry[1])),
        )
        candidate_lines = list(structured_lines)
        candidate_keys = {_normalize_line(line) for line in candidate_lines}
        candidate_lines.extend(
            sentence
            for score, sentence in prose_candidates
            if score > 0
            and len(sentence.split()) >= 4
            and _normalize_line(sentence) not in candidate_keys
        )
        if len(profile.attribute_terms) > 1:
            diversified_lines: list[str] = []
            seen_diversified: set[str] = set()
            for attribute in sorted(
                profile.attribute_terms,
                key=lambda value: (
                    profile.normalized_text.find(value)
                    if value in profile.normalized_text
                    else 10_000,
                    len(value),
                    value,
                ),
            ):
                for candidate in candidate_lines:
                    normalized_candidate = _normalize_line(candidate)
                    if (
                        attribute in normalized_candidate
                        and normalized_candidate not in seen_diversified
                    ):
                        diversified_lines.append(candidate)
                        seen_diversified.add(normalized_candidate)
                        break
            diversified_lines.extend(
                candidate
                for candidate in candidate_lines
                if _normalize_line(candidate) not in seen_diversified
            )
            candidate_lines = diversified_lines
        candidate_lines = candidate_lines[:4]
        if not candidate_lines:
            candidate_lines = _clean_lines(snippet)
        for line in candidate_lines:
            cleaned = _strip_attribute_prefix(line, profile=profile).rstrip(".")
            if (
                not cleaned
                or _is_heading_only_line(cleaned)
                or _is_generic_section_label(cleaned)
            ):
                continue
            rendered_lines.append(cleaned)
            if len(rendered_lines) >= 6:
                break
        if len(rendered_lines) >= 6:
            break

    rendered_lines = _dedupe_preserving_order(rendered_lines)
    if not rendered_lines:
        fallback_item = top_support[0][1]
        return f"{cleaned_snippets[fallback_item.chunk_id]} [{fallback_item.citation_id}]"

    return (
        f"The listed {_format_collection_label(requested_label)} are "
        f"{'; '.join(rendered_lines[:5])} {' '.join(_dedupe_preserving_order(citations))}"
    ).strip()


def _render_action_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str:
    context_phrase = _context_phrase(profile)
    action_lines: list[tuple[str, str]] = []

    for _, item, _ in top_support:
        for line in _section_candidate_lines(item.text):
            normalized = _normalize_line(line)
            if len(normalized.split()) <= 2:
                continue
            if re.search(
                r"\b(architected|built|contributed|created|delivered|designed|developed|implemented|integrated|led|optimized|responsibilities|task|tasks|worked)\b",
                normalized,
            ):
                action_lines.append((line.rstrip("."), item.citation_id))
            if len(action_lines) >= 4:
                break
        if len(action_lines) >= 4:
            break

    deduped_lines: list[tuple[str, str]] = []
    seen_lines: set[str] = set()
    for line, citation_id in action_lines:
        normalized = _normalize_line(line)
        if normalized in seen_lines:
            continue
        seen_lines.add(normalized)
        deduped_lines.append((line, citation_id))

    if not deduped_lines:
        fallback_item = top_support[0][1]
        fallback_text = cleaned_snippets[fallback_item.chunk_id]
        prefix = f"In {context_phrase}, " if context_phrase else ""
        return f"{prefix}{fallback_text} [{fallback_item.citation_id}]".strip()

    role_phrase = None
    company_phrase = None
    for _, item, _ in top_support:
        candidate_lines = [
            line
            for line in _clean_lines(item.text)
            if not _is_heading_only_line(line)
        ]
        for line in candidate_lines[:5]:
            normalized = _normalize_line(line)
            if role_phrase is None and re.search(
                r"\b(engineer|developer|intern|manager|researcher|analyst|lead|consultant)\b",
                normalized,
            ):
                role_phrase = line.rstrip(".")
                continue
            if company_phrase is None and len(line.split()) <= 5 and not re.search(r"\b\d{4}\b", line):
                company_phrase = line.rstrip(".")
        if role_phrase and company_phrase:
            break

    rendered_parts = [
        f"{line} [{citation_id}]"
        for line, citation_id in deduped_lines[:3]
    ]
    if profile.normalized_text.startswith(
        ("does ", "do ", "did ", "has ", "have ", "had ", "is ", "are ", "was ", "were ")
    ) or "if so" in profile.normalized_text:
        where_phrase = ""
        if role_phrase and company_phrase:
            where_phrase = f" She worked as {role_phrase} at {company_phrase}, where"
        elif context_phrase:
            where_phrase = f" In {context_phrase}, the evidence shows"
        return f"Yes.{where_phrase} work included {' '.join(rendered_parts)}".strip()
    if context_phrase:
        return f"In {context_phrase}, the evidence shows work including {' '.join(rendered_parts)}".strip()
    return f"The evidence shows work including {' '.join(rendered_parts)}".strip()


def _render_comparison_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
    cleaned_snippets: dict[str, str],
) -> str:
    numeric_difference = _render_numeric_difference_answer(
        profile=profile,
        top_support=top_support,
    )
    if numeric_difference is not None:
        return numeric_difference

    matching: list[tuple[EvidenceItem, str]] = []
    non_matching: list[tuple[EvidenceItem, str]] = []

    for _, item, _ in top_support:
        cleaned = cleaned_snippets[item.chunk_id]
        if _text_matches_context(item.text, profile=profile) or _text_matches_context(
            cleaned,
            profile=profile,
        ):
            matching.append((item, cleaned))
        else:
            non_matching.append((item, cleaned))

    context_phrase = _context_phrase(profile) or "the referenced context"
    if matching and not non_matching:
        item, cleaned = matching[0]
        return f"Yes. The evidence only shows {requested_attribute_label(profile) or 'that'} in {context_phrase}: {cleaned} [{item.citation_id}]".strip()
    if matching and non_matching:
        match_item, match_cleaned = matching[0]
        other_item, other_cleaned = non_matching[0]
        return (
            f"No. The evidence shows {match_cleaned} [{match_item.citation_id}] "
            f"and also {other_cleaned} [{other_item.citation_id}]."
        ).strip()
    return _render_boolean_answer(
        top_support=top_support,
        cleaned_snippets=cleaned_snippets,
    )


def _render_entity_context_answer(
    *,
    top_support: list[tuple[float, EvidenceItem, str]],
    cleaned_snippets: dict[str, str],
) -> str:
    score, item, _ = top_support[0]
    del score
    cleaned = cleaned_snippets[item.chunk_id]
    return f"Yes. {cleaned} [{item.citation_id}]".strip()


def _count_candidate_items(text: str) -> list[str]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[str] = []
    action_starts = (
        "architected",
        "built",
        "contributed",
        "created",
        "delivered",
        "designed",
        "developed",
        "enhanced",
        "implemented",
        "integrated",
        "optimized",
    )
    for index, raw_line in enumerate(raw_lines):
        line = re.sub(r"^[\s:,\-*\u2022\u00B7]+", "", raw_line).strip()
        if (
            not line
            or _is_heading_only_line(line)
            or "@" in line
            or re.search(r"\b\d{4}\b", line)
        ):
            if ":" not in line or _is_heading_only_line(line) or "@" in line:
                continue
        next_line = raw_lines[index + 1].strip() if index + 1 < len(raw_lines) else ""
        previous_line = raw_lines[index - 1].strip() if index > 0 else ""
        if len(line.split()) > 10:
            continue
        if _normalize_line(line).startswith(action_starts):
            continue
        if ":" in line:
            candidates.append(line.rstrip("."))
            continue
        if (
            next_line.lstrip().startswith(("-", "*", "•"))
            or _is_heading_only_line(previous_line)
            or "–" in line
            or "-" in line
        ):
            candidates.append(line.rstrip("."))
    return _dedupe_preserving_order(candidates)


def _render_count_answer(
    *,
    profile: QueryProfile,
    top_support: list[tuple[float, EvidenceItem, str]],
) -> str:
    explicit_numeric = _select_best_numeric_phrase(
        profile=profile,
        top_support=top_support,
    )
    if explicit_numeric is not None:
        value, citation_id = explicit_numeric
        return f"{value} [{citation_id}]"

    countable_items: list[str] = []
    citations: list[str] = []
    for _, item, _ in top_support:
        citations.append(f"[{item.citation_id}]")
        countable_items.extend(_count_candidate_items(item.text))

    countable_items = _dedupe_preserving_order(countable_items)
    label = requested_attribute_label(profile) or "items"
    if not countable_items:
        fallback_item = top_support[0][1]
        return f"I found relevant {label}, but not enough structured evidence to count them confidently. [{fallback_item.citation_id}]"

    rendered_label = (
        label.rstrip("s") if len(countable_items) == 1 else _format_collection_label(label)
    )

    return (
        f"The evidence shows {len(countable_items)} {rendered_label}: "
        f"{'; '.join(countable_items[:5])} {' '.join(_dedupe_preserving_order(citations))}"
    ).strip()


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

    if is_action_query(profile):
        return _render_action_answer(
            profile=profile,
            top_support=top_support,
        ), cleaned_snippets

    if is_comparison_query(profile):
        return _render_comparison_answer(
            profile=profile,
            top_support=top_support,
            cleaned_snippets=cleaned_snippets,
        ), cleaned_snippets

    if is_entity_context_query(profile):
        return _render_entity_context_answer(
            top_support=top_support,
            cleaned_snippets=cleaned_snippets,
        ), cleaned_snippets

    if is_count_query(profile):
        return _render_count_answer(
            profile=profile,
            top_support=top_support,
        ), cleaned_snippets

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

    if is_collection_query(profile):
        return _render_collection_answer(
            profile=profile,
            top_support=top_support,
        ), cleaned_snippets

    if is_field_extraction_query(profile):
        exact_field_answer = _render_exact_field_answer(
            profile=profile,
            top_support=top_support,
        )
        if exact_field_answer is not None:
            label = requested_attribute_label(profile)
            if label and label not in {"name", "contact", "date"}:
                formatted_label = _format_attribute_prefix(label)
                return f"The {formatted_label} is {exact_field_answer}".strip(), cleaned_snippets
            return exact_field_answer, cleaned_snippets

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
    if is_action_query(profile) or is_comparison_query(profile) or is_entity_context_query(profile):
        return 4
    if is_count_query(profile):
        return 4
    if not is_field_extraction_query(profile):
        return 3
    if is_collection_query(profile):
        return 4
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

    if (
        is_field_extraction_query(profile)
        or is_action_query(profile)
        or is_comparison_query(profile)
        or is_entity_context_query(profile)
        or is_count_query(profile)
    ):
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
    if (
        is_action_query(profile)
        or is_comparison_query(profile)
        or is_entity_context_query(profile)
        or is_count_query(profile)
    ):
        support_threshold = max(best_score * 0.45, best_score - 6.0)
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

    if is_dataset_summary_query(profile):
        summary_title_entry = next(
            (
                entry
                for entry in ranked_support
                if _looks_like_document_title_line(entry[2])
                or any(
                    _looks_like_document_title_line(line)
                    for line in _clean_lines(entry[1].text)[:2]
                )
                or entry[1].chunk_index == 0
            ),
            None,
        )
        if summary_title_entry is not None and all(
            item.chunk_id != summary_title_entry[1].chunk_id
            for _, item, _ in top_support
        ):
            top_support = [summary_title_entry, *top_support]
            top_support = sorted(
                top_support,
                key=lambda entry: (
                    entry[1].chunk_index,
                    -entry[0],
                    entry[1].chunk_id,
                ),
            )[:max_support_items]

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
