"""Shared query analysis helpers for retrieval and grounded answering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal


QueryKind = Literal[
    "summary",
    "definition",
    "boolean",
    "list",
    "lookup",
    "action",
    "comparison",
    "entity",
    "count",
    "open",
]

_STOPWORDS = {
    "a", "about", "an", "and", "are", "at", "by", "can", "could", "do", "does",
    "for", "from", "had", "has", "have", "he", "hello", "help", "her", "hers",
    "him", "his", "how", "i", "in", "into", "is", "it", "its", "just", "me",
    "my", "of", "on", "or", "our", "please", "she", "than", "that", "the",
    "their", "them", "there", "these", "they", "this", "those", "to", "us",
    "was", "we", "what", "when", "where", "which", "who", "with", "would",
    "you", "your",
}

_ATTRIBUTE_NOISE_TOKENS = {
    "attached", "dataset", "datasets", "document", "documents", "entry", "file",
    "files", "item", "items", "person", "people", "profile", "record", "records",
    "resume", "thing",
}

_CANONICAL_ATTRIBUTE_SYNONYMS = {
    "name": {"full name", "fullname", "identity", "name", "owner", "title"},
    "contact": {"address", "contact", "email", "github", "linkedin", "mail", "number", "phone", "website"},
    "date": {"date", "deadline", "duration", "month", "period", "schedule", "time", "timeline", "year"},
    "location": {"address", "city", "country", "location", "place", "where"},
}

_COLLECTION_ATTRIBUTE_HINTS = {
    "achievement", "achievements", "award", "awards", "benefit", "benefits",
    "capability", "capabilities", "certificate", "certificates", "component",
    "components", "feature", "features", "framework", "frameworks", "language",
    "languages", "project", "projects", "requirement", "requirements",
    "responsibility", "responsibilities", "role", "roles", "section", "sections",
    "service", "services", "skill", "skills", "technology", "technologies",
    "tool", "tools",
}

_GENERIC_QUERY_VOCABULARY = {
    "about", "achievement", "achievements", "address", "answer", "attribute",
    "attributes", "award", "awards", "categories", "category", "certificate",
    "certificates", "compare", "comparison", "contact", "contain", "contains",
    "count", "dataset", "datasets", "date", "definition", "details", "difference",
    "document", "documents", "education", "email", "employment", "entity",
    "experience", "feature", "features", "field", "fields", "file", "files",
    "framework", "frameworks", "fullname", "github", "history", "identity",
    "include", "includes", "information", "introduction", "item", "items",
    "language", "languages", "list", "location", "mail", "meaning", "mention",
    "model", "name", "number", "only", "other", "overview", "owner", "pattern",
    "person", "people", "phone", "pricing", "profile", "project", "projects",
    "record", "records", "recognition", "refers", "responsibilities",
    "responsibility", "resume", "role", "roles", "section", "sections", "service",
    "services", "skill", "skills", "summary", "support", "supported", "supports",
    "technical", "technology", "technologies", "title", "tool", "tools", "total",
    "website", "work", "worked",
}

_ATTRIBUTE_EXPANSION_HINTS = {
    "award": {"achievement", "recognition", "honor"},
    "contact": {"email", "phone", "address"},
    "count": {"number", "total"},
    "experience": {"employment", "professional", "role", "work"},
    "history": {"employment", "experience", "timeline"},
    "name": {"full name", "identity", "title"},
    "pricing": {"cost", "plan", "subscription"},
    "project": {"build", "portfolio"},
    "projects": {"build", "portfolio"},
    "role": {"responsibility", "responsibilities"},
    "roles": {"responsibility", "responsibilities"},
    "skill": {"capabilities", "frameworks", "languages", "technical", "tools"},
    "skills": {"capabilities", "frameworks", "languages", "technical", "tools"},
    "summary": {"introduction", "overview"},
}

_SUMMARY_QUERY_NOISE = {
    "attached", "contain", "contains", "cover", "covers", "data", "dataset",
    "datasets", "document", "documents", "file", "files", "include", "includes",
    "information", "item", "items", "overview", "record", "records", "summary",
}

_SUMMARY_QUERY_PATTERN = re.compile(
    r"^(?:what\s+is\s+(?:the\s+)?(?:dataset|document|file|record|profile|resume)\s+about|"
    r"summari[sz]e\s+(?:the\s+)?(?:dataset|document|file|record|profile|resume)|"
    r"what\s+does\s+(?:the\s+)?(?:dataset|document|file|record|profile|resume)\s+(?:contain|cover)|"
    r"give\s+me\s+an?\s+overview(?:\s+of\s+.+)?)\b"
)
_DEFINITION_QUERY_PATTERN = re.compile(r"^(?:what\s+(?:is|does)\s+.+?\s+(?:mean|means)\??|define\s+.+)$")
_BOOLEAN_QUERY_PATTERN = re.compile(r"^(?:is|are|was|were|do|does|did|has|have|had|can|could|should|would)\b")
_LIST_QUERY_PATTERN = re.compile(r"^(?:what\s+are|which|list|show\s+me|give\s+me|tell\s+me)\b")
_COUNT_QUERY_PATTERN = re.compile(r"^(?:how\s+many|number\s+of|count\s+(?:the\s+)?)\b")
_ACTION_QUERY_PATTERN = re.compile(r"^(?:what\s+(?:did|does)\b|describe\b|summari[sz]e\b).*\b(?:do|did|does|work|responsibilit(?:y|ies)|contribution|contributions|task|tasks)\b")
_ATTRIBUTE_PATTERNS = [
    re.compile(r"^(?:what|which)\s+(?:is|are|was|were)\s+(?:the\s+)?(?P<attribute>.+?)(?:\s+(?:of|for|in|on|from|at|with)\b|$)"),
    re.compile(r"^(?:list|show\s+me|give\s+me|tell\s+me)\s+(?:the\s+)?(?P<attribute>.+?)(?:\s+(?:of|for|in|on|from|at|with)\b|$)"),
    re.compile(r"^(?:how\s+many|number\s+of|count\s+(?:the\s+)?)\s*(?P<attribute>.+?)(?:\s+(?:are|does|do|did|has|have|had|can|could|should|would)\b|$)"),
    re.compile(r"^(?:what|which)\s+(?P<attribute>.+?)\s+(?:are|is)\s+(?:include|included|available|list|listed|provide|provided|support|supported)\b"),
    re.compile(r"^(?:what|which)\s+(?P<attribute>.+?)\s+(?:does|do|did|has|have|had|can|could|should|would)\b"),
    re.compile(r"^(?:who\s+is\s+(?:the\s+)?)(?P<attribute>.+?)(?:\s+(?:of|for|in|on|from|at|with)\b|$)"),
]
_FOLLOW_UP_PREFIXES = ("and ", "also ", "how about", "what about", "what else", "and what", "and how")
_REFERENCE_ONLY_PATTERN = re.compile(r"^(?:and\s+)?(?:what\s+about\s+)?(?:it|that|this|those|these|them|there|here)\b")
_REFERENCE_MARKER_PATTERN = re.compile(r"\b(?:it|that|this|those|these|them|there|here|former|latter|second|first)\b")
_DOCUMENT_REFERENCE_PATTERN = re.compile(r"\b(?P<ordinal>first|second|third)\s+document\b")
_CONTEXT_PREPOSITION_PATTERN = re.compile(r"\b(?:at|in|on|for|with|about|under|within|inside)\s+(?P<context>.+)$")
_CONTEXT_BREAK_TOKENS = {"and", "another", "any", "because", "but", "else", "if", "only", "or", "than", "there", "whether"}
_ACTION_HINT_TERMS = {
    "action", "actions", "architected", "build", "built", "contribute",
    "contributed", "contribution", "contributions", "create", "created",
    "deliver", "delivered", "design", "designed", "develop", "developed", "do",
    "did", "implement", "implemented", "integrated", "lead", "led", "optimize",
    "optimized", "responsibilities", "responsibility", "support", "supported",
    "task", "tasks", "work", "worked",
}
_COMPARISON_MARKERS = {"another", "compare", "compared", "difference", "different", "else", "only", "other", "outside", "same", "versus", "vs"}
_ENTITY_CONTEXT_HINTS = {"build", "built", "contribute", "contributed", "mention", "mentioned", "support", "supported", "use", "used", "work", "worked"}
_NAME_LINE_PATTERN = re.compile(r"^[A-Z][A-Za-z'\u2019-]+(?:\s+[A-Z][A-Za-z'\u2019-]+){1,4}$")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_DATE_PATTERN = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\b", re.IGNORECASE)
_HEADING_CANDIDATE_PATTERN = re.compile(r"^(?:[A-Z][A-Z0-9/&,\- ]{2,}|[A-Z][A-Za-z0-9/&,\- ]{1,48}:)\s*$")


@dataclass(frozen=True)
class QueryProfile:
    """Normalized query understanding shared by retrieval and answering."""

    raw_text: str
    normalized_text: str
    terms: frozenset[str]
    expanded_terms: frozenset[str]
    attribute_terms: frozenset[str]
    context_terms: frozenset[str]
    semantic_tags: frozenset[str]
    query_kind: QueryKind
    document_reference_rank: int | None = None


@dataclass(frozen=True)
class QueryPlan:
    """One lightweight Standard query plan used across retrieval and answering."""

    raw_query_text: str
    resolved_query_text: str
    profile: QueryProfile
    retrieval_query_text: str
    retrieval_queries: tuple[str, ...]
    explanation: str
    used_conversation_context: bool


@dataclass(frozen=True)
class ConversationContext:
    """Small deterministic memory distilled from recent conversation turns."""

    recent_user_queries: tuple[str, ...]
    recent_assistant_messages: tuple[str, ...]
    carried_attribute_terms: tuple[str, ...]
    carried_context_terms: tuple[str, ...]
    carried_semantic_tags: tuple[str, ...]
    carried_focus_terms: tuple[str, ...]
    last_query_kind: QueryKind | None
    last_document_reference_rank: int | None = None


def _normalize_token(token: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", token.casefold())
    if normalized and normalized.isalpha():
        normalized = _correct_query_token(normalized)
    if normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized


def _normalize_text(text: str) -> str:
    normalized_tokens: list[str] = []
    for token in re.findall(r"[A-Za-z0-9]+", text):
        normalized = _normalize_token(token)
        if normalized:
            normalized_tokens.append(normalized)
    return " ".join(normalized_tokens).strip()


def _dedupe_texts(values: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value.strip())
    return tuple(deduped)


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    """Return non-empty values with stable first-seen ordering."""

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value.strip())
    return tuple(deduped)


def _fuzzy_token_match(candidate: str, target: str, *, threshold: float = 0.84) -> bool:
    normalized_candidate = _normalize_token(candidate)
    normalized_target = _normalize_token(target)
    if not normalized_candidate or not normalized_target:
        return False
    if normalized_candidate == normalized_target:
        return True
    if abs(len(normalized_candidate) - len(normalized_target)) > 3:
        return False
    return SequenceMatcher(a=normalized_candidate, b=normalized_target).ratio() >= threshold


def _correct_query_token(token: str) -> str:
    """Apply conservative typo correction for generic query vocabulary."""

    normalized = re.sub(r"[^a-z0-9]+", "", token.casefold())
    if (
        not normalized
        or normalized in _GENERIC_QUERY_VOCABULARY
        or normalized.isdigit()
        or len(normalized) < 5
    ):
        return normalized

    best_match = normalized
    best_score = 0.0
    for candidate in _GENERIC_QUERY_VOCABULARY:
        if abs(len(candidate) - len(normalized)) > 2 or candidate[:1] != normalized[:1]:
            continue
        score = SequenceMatcher(a=normalized, b=candidate).ratio()
        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match if best_score >= 0.86 else normalized


def _token_expansion_forms(token: str) -> set[str]:
    """Return conservative morphological variants for retrieval and matching."""

    normalized = _normalize_token(token)
    if not normalized or len(normalized) < 4:
        return set()

    variants = {normalized}
    if normalized.endswith("ing") and len(normalized) > 5:
        stem = normalized[:-3]
        if len(stem) >= 3:
            variants.update({stem, f"{stem}e", f"{stem}er"})
    elif normalized.endswith(("er", "or", "ed")) and len(normalized) > 4:
        stem = normalized[:-2]
        if len(stem) >= 3:
            variants.update({stem, f"{stem}e", f"{stem}ing"})

    for token_variant in list(variants):
        for hint in _ATTRIBUTE_EXPANSION_HINTS.get(token_variant, set()):
            variants.add(_normalize_token(hint))

    return {variant for variant in variants if len(variant) >= 4}


def _terms_contain_token(terms: set[str], token: str) -> bool:
    normalized_token = _normalize_token(token)
    if not normalized_token:
        return False
    if normalized_token in terms:
        return True
    return any(_fuzzy_token_match(candidate, normalized_token) for candidate in terms)


def _contains_phrase(*, normalized_text: str, terms: set[str], phrase: str) -> bool:
    normalized_phrase = _normalize_text(phrase)
    if not normalized_phrase:
        return False
    if normalized_phrase in normalized_text:
        return True
    phrase_tokens = [
        _normalize_token(token)
        for token in normalized_phrase.split()
        if _normalize_token(token)
    ]
    return bool(phrase_tokens) and all(_terms_contain_token(terms, token) for token in phrase_tokens)


def _looks_like_name_line(line: str) -> bool:
    candidate = line.strip()
    if not candidate or candidate.isupper() or any(char.isdigit() for char in candidate):
        return False
    return bool(_NAME_LINE_PATTERN.match(candidate))


def _is_heading_only_line(line: str) -> bool:
    candidate = line.strip().rstrip(":")
    return bool(candidate and _HEADING_CANDIDATE_PATTERN.fullmatch(candidate))


def tokenize_meaningful_terms(text: str) -> set[str]:
    """Return normalized non-trivial terms from free text."""

    normalized_terms: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9]+", text):
        normalized = _normalize_token(token)
        if not normalized or len(normalized) < 3 or normalized in _STOPWORDS:
            continue
        normalized_terms.add(normalized)
        normalized_terms.update(_token_expansion_forms(normalized))
    return normalized_terms


def _extract_context_terms(*, normalized_text: str) -> set[str]:
    """Extract generic contextual targets like company, project, or topic phrases."""

    context_terms: set[str] = set()
    for match in _CONTEXT_PREPOSITION_PATTERN.finditer(normalized_text):
        raw_context = match.group("context").strip()
        tokens: list[str] = []
        for token in raw_context.split():
            normalized = _normalize_token(token)
            if not normalized:
                continue
            if normalized in _CONTEXT_BREAK_TOKENS:
                break
            if normalized in _STOPWORDS:
                continue
            tokens.append(normalized)
            if len(tokens) >= 4:
                break
        if tokens:
            context_terms.add(" ".join(tokens))
    return context_terms


def _document_reference_rank(normalized_text: str) -> int | None:
    """Extract a lightweight 1-based document ordinal reference when present."""

    match = _DOCUMENT_REFERENCE_PATTERN.search(normalized_text)
    if not match:
        return None
    ordinal = match.group("ordinal")
    return {"first": 1, "second": 2, "third": 3}.get(ordinal)


def _extract_attribute_terms(*, normalized_text: str, terms: set[str]) -> set[str]:
    """Extract generic attribute phrases like work experience or pricing model."""

    attribute_terms: set[str] = set()

    for pattern in _ATTRIBUTE_PATTERNS:
        match = pattern.match(normalized_text)
        if not match:
            continue
        raw_attribute = match.group("attribute").strip()
        cleaned_tokens: list[str] = []
        for token in raw_attribute.split():
            normalized = _normalize_token(token)
            if (
                not normalized
                or normalized in _ATTRIBUTE_NOISE_TOKENS
                or normalized in _STOPWORDS
            ):
                continue
            cleaned_tokens.append(normalized)
        if cleaned_tokens:
            attribute_terms.add(" ".join(cleaned_tokens[:4]))

    for canonical, synonyms in _CANONICAL_ATTRIBUTE_SYNONYMS.items():
        if any(
            _contains_phrase(
                normalized_text=normalized_text,
                terms=terms,
                phrase=synonym,
            )
            for synonym in synonyms
        ):
            attribute_terms.add(canonical)

    return {term for term in attribute_terms if term}


def _build_semantic_tags(*, normalized_text: str, terms: set[str]) -> set[str]:
    """Infer small universal attribute families without dataset-specific domains."""

    semantic_tags: set[str] = set()
    for canonical, synonyms in _CANONICAL_ATTRIBUTE_SYNONYMS.items():
        if any(
            _contains_phrase(
                normalized_text=normalized_text,
                terms=terms,
                phrase=synonym,
            )
            for synonym in synonyms
        ):
            semantic_tags.add(canonical)
    return semantic_tags


def _assistant_focus_terms(text: str) -> list[str]:
    """Extract a few salient phrases from assistant replies for follow-up grounding."""

    candidates: list[str] = []
    lines = [line.strip(" -*:\t") for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        if _is_heading_only_line(line):
            continue
        if _looks_like_name_line(line):
            candidates.append(line)
            continue
        if ":" in line and len(line) <= 120:
            label, value = line.split(":", 1)
            label_terms = tokenize_meaningful_terms(label)
            value_terms = tokenize_meaningful_terms(value)
            if label_terms and value_terms:
                candidates.append(f"{label.strip()}: {value.strip()}")
                continue
        for match in re.finditer(
            r"\b[A-Z][A-Za-z0-9&+/#'-]*(?:\s+[A-Z][A-Za-z0-9&+/#'-]*){1,3}\b",
            line,
        ):
            phrase = match.group(0).strip()
            if _is_heading_only_line(phrase):
                continue
            candidates.append(phrase)
    return list(_dedupe_preserve_order(candidates))[:8]


def _is_summary_query(*, normalized_text: str, terms: set[str]) -> bool:
    if _SUMMARY_QUERY_PATTERN.match(normalized_text):
        return True
    dataset_like = any(
        _terms_contain_token(terms, token)
        for token in {"dataset", "document", "file", "profile", "record", "resume"}
    )
    summary_like = any(
        token in normalized_text
        for token in {
            " about",
            " contain",
            " cover",
            "overview",
            "summarize",
            "summary",
        }
    ) or normalized_text.endswith("about")
    return dataset_like and summary_like


def _attribute_is_collection_like(attribute: str) -> bool:
    normalized_attribute = _normalize_text(attribute)
    if not normalized_attribute:
        return False
    tokens = {
        _normalize_token(token)
        for token in normalized_attribute.split()
        if _normalize_token(token)
    }
    return any(token in _COLLECTION_ATTRIBUTE_HINTS for token in tokens)


def _comparison_marker_present(*, normalized_text: str, terms: set[str]) -> bool:
    return any(_terms_contain_token(terms, marker) for marker in _COMPARISON_MARKERS) or any(
        marker in normalized_text
        for marker in (" only ", " other ", " another ", " else ", " vs ", " versus ")
    )


def _classify_query_kind(
    *,
    normalized_text: str,
    terms: set[str],
    attribute_terms: set[str],
    semantic_tags: set[str],
    context_terms: set[str],
) -> QueryKind:
    """Map a query into a generic question shape."""

    del semantic_tags  # Captured via attribute terms and downstream scoring.

    if _is_summary_query(normalized_text=normalized_text, terms=terms):
        return "summary"
    if _DEFINITION_QUERY_PATTERN.match(normalized_text):
        return "definition"
    if _COUNT_QUERY_PATTERN.match(normalized_text):
        return "count"

    boolean_like = bool(_BOOLEAN_QUERY_PATTERN.match(normalized_text))
    if boolean_like and _comparison_marker_present(
        normalized_text=normalized_text,
        terms=terms,
    ):
        return "comparison"
    if _ACTION_QUERY_PATTERN.match(normalized_text):
        return "action"
    if boolean_like and context_terms and any(
        _terms_contain_token(terms, token) for token in _ENTITY_CONTEXT_HINTS
    ):
        return "entity"
    if boolean_like:
        return "boolean"
    if _LIST_QUERY_PATTERN.match(normalized_text):
        return "list" if attribute_terms else "open"
    if any(_attribute_is_collection_like(attribute) for attribute in attribute_terms):
        return "list"
    if attribute_terms:
        return "lookup"
    if context_terms and any(
        _terms_contain_token(terms, token) for token in _ACTION_HINT_TERMS
    ):
        return "action"
    return "open"


def _is_follow_up_like_query(profile: QueryProfile) -> bool:
    normalized = profile.normalized_text
    if not normalized:
        return False
    if normalized.startswith(_FOLLOW_UP_PREFIXES):
        return True
    if _REFERENCE_ONLY_PATTERN.match(normalized):
        return True
    if _REFERENCE_MARKER_PATTERN.search(normalized):
        return True
    if profile.document_reference_rank is not None:
        return True
    return (
        len(profile.terms) <= 2
        and not profile.attribute_terms
        and not profile.context_terms
    )


def _resolve_follow_up_context(
    *,
    query_text: str,
    profile: QueryProfile,
    previous_user_query: str | None,
    conversation_context: ConversationContext | None = None,
) -> tuple[str, bool]:
    """Optionally enrich an underspecified follow-up using the prior user turn."""

    if conversation_context is None and previous_user_query is not None:
        conversation_context = build_conversation_context(
            recent_user_queries=[previous_user_query],
        )
    if conversation_context is None:
        return query_text, False
    if not _is_follow_up_like_query(profile):
        return query_text, False

    context_fragments: list[str] = []
    if (
        profile.document_reference_rank is None
        and conversation_context.last_document_reference_rank is not None
        and _REFERENCE_MARKER_PATTERN.search(profile.normalized_text)
    ):
        ordinal = {
            1: "first document",
            2: "second document",
            3: "third document",
        }.get(conversation_context.last_document_reference_rank)
        if ordinal is not None:
            context_fragments.append(ordinal)
    if not profile.attribute_terms and conversation_context.carried_attribute_terms:
        context_fragments.extend(conversation_context.carried_attribute_terms[:2])
    if not profile.context_terms and conversation_context.carried_context_terms:
        context_fragments.extend(conversation_context.carried_context_terms[:2])
    if not profile.semantic_tags and conversation_context.carried_semantic_tags:
        context_fragments.extend(conversation_context.carried_semantic_tags[:2])
    if (
        profile.document_reference_rank is not None
        and conversation_context.last_query_kind == "summary"
    ):
        context_fragments.extend(["dataset", "summary", "overview"])
    if (
        not profile.context_terms
        and profile.query_kind in {"action", "comparison", "entity", "open"}
        and conversation_context.carried_focus_terms
    ):
        context_fragments.extend(conversation_context.carried_focus_terms[:4])
    if not context_fragments:
        return query_text, False

    resolved_query_text = f"{query_text.strip()} context {' '.join(_dedupe_preserve_order(context_fragments))}"
    return resolved_query_text.strip(), True


def build_conversation_context(
    *,
    recent_user_queries: list[str] | tuple[str, ...],
    recent_assistant_messages: list[str] | tuple[str, ...] = (),
) -> ConversationContext | None:
    """Compress recent conversation turns into a small reusable memory object."""

    user_queries = [query.strip() for query in recent_user_queries if query and query.strip()]
    assistant_messages = [
        message.strip()
        for message in recent_assistant_messages
        if message and message.strip()
    ]
    if not user_queries and not assistant_messages:
        return None

    recent_profiles = [build_query_profile(query) for query in user_queries[-4:]]
    ordered_recent_profiles = list(reversed(recent_profiles))

    carried_attribute_terms: list[str] = []
    carried_context_terms: list[str] = []
    carried_semantic_tags: list[str] = []
    carried_focus_terms: list[str] = []

    for profile in ordered_recent_profiles:
        carried_attribute_terms.extend(sorted(profile.attribute_terms))
        carried_context_terms.extend(sorted(profile.context_terms))
        carried_semantic_tags.extend(sorted(profile.semantic_tags))
        for attribute in sorted(profile.attribute_terms):
            carried_focus_terms.append(attribute)
        for context in sorted(profile.context_terms):
            carried_focus_terms.append(context)
        for term in sorted(profile.terms):
            if (
                len(term) >= 4
                and term not in _GENERIC_QUERY_VOCABULARY
                and term not in _ATTRIBUTE_NOISE_TOKENS
            ):
                carried_focus_terms.append(term)

    recent_assistant_phrases: list[str] = []
    for message in reversed(assistant_messages[-2:]):
        recent_assistant_phrases.extend(_assistant_focus_terms(message))

    for phrase in recent_assistant_phrases:
        carried_focus_terms.append(phrase)
        normalized_phrase = _normalize_text(phrase)
        if " " in normalized_phrase:
            carried_context_terms.append(normalized_phrase)

    most_recent_profile = ordered_recent_profiles[0] if ordered_recent_profiles else None
    return ConversationContext(
        recent_user_queries=tuple(user_queries[-4:]),
        recent_assistant_messages=tuple(assistant_messages[-2:]),
        carried_attribute_terms=_dedupe_preserve_order(carried_attribute_terms),
        carried_context_terms=_dedupe_preserve_order(carried_context_terms),
        carried_semantic_tags=_dedupe_preserve_order(carried_semantic_tags),
        carried_focus_terms=_dedupe_preserve_order(carried_focus_terms),
        last_query_kind=most_recent_profile.query_kind if most_recent_profile is not None else None,
        last_document_reference_rank=(
            most_recent_profile.document_reference_rank
            if most_recent_profile is not None
            else None
        ),
    )


def build_query_profile(query_text: str) -> QueryProfile:
    """Build one reusable query profile from the user's text."""

    normalized_text = _normalize_text(query_text)
    terms = tokenize_meaningful_terms(query_text)
    context_terms = _extract_context_terms(normalized_text=normalized_text)
    document_reference_rank = _document_reference_rank(normalized_text)
    attribute_terms = _extract_attribute_terms(
        normalized_text=normalized_text,
        terms=terms,
    )
    semantic_tags = _build_semantic_tags(
        normalized_text=normalized_text,
        terms=terms,
    )
    query_kind = _classify_query_kind(
        normalized_text=normalized_text,
        terms=terms,
        attribute_terms=attribute_terms,
        semantic_tags=semantic_tags,
        context_terms=context_terms,
    )

    mutable_attribute_terms = set(attribute_terms)
    if query_kind == "action" and not mutable_attribute_terms:
        mutable_attribute_terms.add("responsibilities")
    if query_kind == "comparison" and not mutable_attribute_terms:
        if any(
            _terms_contain_token(terms, token)
            for token in {"career", "employment", "experience", "job", "role", "work"}
        ):
            mutable_attribute_terms.add("experience")

    expanded_terms = set(terms)
    for attribute in mutable_attribute_terms:
        expanded_terms.update(tokenize_meaningful_terms(attribute))
        for token in attribute.split():
            expanded_terms.update(_token_expansion_forms(token))

    for context in context_terms:
        expanded_terms.update(tokenize_meaningful_terms(context))
        for token in context.split():
            expanded_terms.update(_token_expansion_forms(token))

    for semantic_tag in semantic_tags:
        expanded_terms.update(
            tokenize_meaningful_terms(
                " ".join(_CANONICAL_ATTRIBUTE_SYNONYMS[semantic_tag])
            )
        )
    for term in list(terms):
        expanded_terms.update(_token_expansion_forms(term))

    if query_kind == "summary":
        expanded_terms.update({"overview", "summary", "introduction", "profile"})
    elif query_kind == "definition":
        expanded_terms.update({"definition", "explains", "means", "refers"})
    elif query_kind == "list":
        expanded_terms.update({"categories", "items", "list"})
    elif query_kind == "count":
        expanded_terms.update({"count", "number", "total"})
    elif query_kind == "action":
        expanded_terms.update(
            {
                "build",
                "contribution",
                "contributions",
                "develop",
                "developed",
                "responsibilities",
                "responsibility",
                "task",
                "tasks",
                "work",
            }
        )
    elif query_kind == "comparison":
        expanded_terms.update({"another", "compare", "else", "only", "other"})
    elif query_kind == "entity":
        expanded_terms.update({"mention", "project", "support", "used", "work"})

    return QueryProfile(
        raw_text=query_text,
        normalized_text=normalized_text,
        terms=frozenset(terms),
        expanded_terms=frozenset(expanded_terms),
        attribute_terms=frozenset(mutable_attribute_terms),
        context_terms=frozenset(context_terms),
        semantic_tags=frozenset(semantic_tags),
        query_kind=query_kind,
        document_reference_rank=document_reference_rank,
    )


def _build_retrieval_query_variants(profile: QueryProfile) -> tuple[str, ...]:
    """Build a small set of retrieval rewrites for one generic query profile."""

    variants: list[str] = [build_retrieval_query_text(profile)]
    core_terms = sorted(profile.terms)
    context_terms = sorted(profile.context_terms)

    if profile.attribute_terms:
        for attribute in sorted(profile.attribute_terms)[:2]:
            attribute_terms = tokenize_meaningful_terms(attribute)
            remaining_terms = [
                term
                for term in [*context_terms, *core_terms]
                if term not in attribute_terms
            ][:5]
            variants.append(" ".join([attribute, *remaining_terms]).strip())

    if profile.semantic_tags:
        for semantic_tag in sorted(profile.semantic_tags)[:2]:
            variants.append(
                " ".join(
                    [
                        semantic_tag,
                        *sorted(
                            _CANONICAL_ATTRIBUTE_SYNONYMS.get(semantic_tag, set())
                        )[:2],
                        *core_terms[:3],
                    ]
                ).strip()
            )

    if is_definition_query(profile):
        subject_terms = sorted(profile.attribute_terms) or core_terms[:3]
        if subject_terms:
            variants.append(" ".join([*subject_terms, "definition", "meaning"]).strip())

    if is_dataset_summary_query(profile):
        variants.append("dataset document overview summary introduction")

    if is_collection_query(profile):
        collection_terms = sorted(profile.attribute_terms) or core_terms[:3]
        if collection_terms:
            variants.append(" ".join([*collection_terms, "list", "items"]).strip())

    if is_count_query(profile):
        count_terms = sorted(profile.attribute_terms) or core_terms[:3]
        if count_terms:
            variants.append(" ".join([*count_terms, "count", "total", "number"]).strip())

    if is_action_query(profile):
        action_terms = sorted(profile.attribute_terms) or ["responsibilities"]
        variants.append(
            " ".join(
                [
                    *context_terms[:3],
                    *action_terms[:2],
                    "responsibilities",
                    "contributions",
                    "tasks",
                ]
            ).strip()
        )

    if is_entity_context_query(profile):
        variants.append(
            " ".join([*context_terms[:3], *core_terms[:3], "work", "project", "mention"]).strip()
        )

    if is_comparison_query(profile):
        comparison_terms = sorted(profile.attribute_terms) or core_terms[:3]
        variants.append(
            " ".join(
                [*context_terms[:3], *comparison_terms[:2], "compare", "other", "another"]
            ).strip()
        )

    if is_boolean_query(profile) and (profile.attribute_terms or profile.context_terms):
        variants.append(" ".join([*sorted(profile.attribute_terms), *context_terms]).strip())

    return _dedupe_texts(variants)


def explain_query_plan(plan: QueryPlan) -> str:
    """Render a short explanation of how Standard interpreted the query."""

    explanation_parts = [f"kind={plan.profile.query_kind}"]
    if plan.profile.attribute_terms:
        explanation_parts.append(
            "attributes=" + ", ".join(sorted(plan.profile.attribute_terms))
        )
    if plan.profile.context_terms:
        explanation_parts.append(
            "context=" + ", ".join(sorted(plan.profile.context_terms))
        )
    if plan.profile.document_reference_rank is not None:
        explanation_parts.append(f"document_reference_rank={plan.profile.document_reference_rank}")
    if plan.profile.semantic_tags:
        explanation_parts.append(
            "semantic_tags=" + ", ".join(sorted(plan.profile.semantic_tags))
        )
    if plan.used_conversation_context:
        explanation_parts.append("used_conversation_context=true")
    if len(plan.retrieval_queries) > 1:
        explanation_parts.append(f"retrieval_rewrites={len(plan.retrieval_queries)}")
    return "; ".join(explanation_parts)


def build_query_plan(
    query_text: str,
    *,
    previous_user_query: str | None = None,
    conversation_context: ConversationContext | None = None,
) -> QueryPlan:
    """Build one Standard query plan with lightweight rewriting and explanation."""

    initial_profile = build_query_profile(query_text)
    resolved_query_text, used_conversation_context = _resolve_follow_up_context(
        query_text=query_text,
        profile=initial_profile,
        previous_user_query=previous_user_query,
        conversation_context=conversation_context,
    )
    profile = (
        initial_profile
        if resolved_query_text == query_text
        else build_query_profile(resolved_query_text)
    )
    retrieval_query_text = build_retrieval_query_text(profile)
    retrieval_queries = _build_retrieval_query_variants(profile)
    plan = QueryPlan(
        raw_query_text=query_text,
        resolved_query_text=resolved_query_text,
        profile=profile,
        retrieval_query_text=retrieval_query_text,
        retrieval_queries=retrieval_queries,
        explanation="",
        used_conversation_context=used_conversation_context,
    )
    return QueryPlan(
        raw_query_text=plan.raw_query_text,
        resolved_query_text=plan.resolved_query_text,
        profile=plan.profile,
        retrieval_query_text=plan.retrieval_query_text,
        retrieval_queries=plan.retrieval_queries,
        explanation=explain_query_plan(plan),
        used_conversation_context=plan.used_conversation_context,
    )


def query_plan_metadata(plan: QueryPlan) -> dict[str, Any]:
    """Serialize a query plan into trace-safe metadata."""

    return {
        "raw_query_text": plan.raw_query_text,
        "resolved_query_text": plan.resolved_query_text,
        "query_kind": plan.profile.query_kind,
        "attribute_terms": list(sorted(plan.profile.attribute_terms)),
        "context_terms": list(sorted(plan.profile.context_terms)),
        "document_reference_rank": plan.profile.document_reference_rank,
        "semantic_tags": list(sorted(plan.profile.semantic_tags)),
        "retrieval_query_text": plan.retrieval_query_text,
        "retrieval_queries": list(plan.retrieval_queries),
        "explanation": plan.explanation,
        "used_conversation_context": plan.used_conversation_context,
    }


def is_definition_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a definition or explanation."""

    return profile.query_kind == "definition"


def is_boolean_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a yes/no style answer."""

    return profile.query_kind in {"boolean", "comparison", "entity"}


def is_action_query(profile: QueryProfile) -> bool:
    """Return whether the query asks what someone or something did."""

    return profile.query_kind == "action"


def is_comparison_query(profile: QueryProfile) -> bool:
    """Return whether the query compares one context against alternatives."""

    return profile.query_kind == "comparison"


def is_entity_context_query(profile: QueryProfile) -> bool:
    """Return whether the query asks about one entity within a context."""

    return profile.query_kind == "entity"


def is_count_query(profile: QueryProfile) -> bool:
    """Return whether the query asks for a grounded count."""

    return profile.query_kind == "count"


def is_dataset_summary_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a broad summary of the attached data."""

    return profile.query_kind == "summary"


def primary_intent(profile: QueryProfile) -> str | None:
    """Return the most important attribute or semantic cue in the query."""

    for semantic_tag in ("name", "contact", "date", "location"):
        if semantic_tag in profile.semantic_tags:
            return semantic_tag
    if profile.attribute_terms:
        return sorted(
            profile.attribute_terms,
            key=lambda value: (len(value.split()), len(value)),
        )[0]
    return None


def requested_attribute_label(profile: QueryProfile) -> str | None:
    """Return a human-facing requested attribute label when one exists."""

    intent = primary_intent(profile)
    if intent is None:
        return None
    return intent.replace("_", " ").strip()


def is_collection_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a collection-like answer."""

    return profile.query_kind == "list" or any(
        _attribute_is_collection_like(attribute)
        for attribute in profile.attribute_terms
    )


def is_field_extraction_query(profile: QueryProfile) -> bool:
    """Return whether the query asks for one focused attribute rather than open summarization."""

    return profile.query_kind in {"lookup", "list"} and bool(
        profile.attribute_terms or profile.semantic_tags
    )


def _heading_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()][:4]


def score_text_against_query(
    text: str,
    *,
    profile: QueryProfile,
    chunk_index: int | None = None,
) -> float:
    """Score how directly one text block can answer the current query."""

    text_terms = tokenize_meaningful_terms(text)
    normalized_text = _normalize_text(text)
    direct_overlap = len(profile.terms & text_terms)
    expanded_overlap = len(profile.expanded_terms & text_terms)
    score = direct_overlap * 8.0 + expanded_overlap * 2.5

    heading_candidates = _heading_lines(text)
    for attribute in profile.attribute_terms:
        if attribute in normalized_text:
            score += 4.5
        if any(
            attribute in _normalize_text(candidate)
            for candidate in heading_candidates
        ):
            score += 6.5

    context_overlap = 0
    for context in profile.context_terms:
        if context in normalized_text:
            score += 6.0
            context_overlap += 1
        else:
            context_terms = tokenize_meaningful_terms(context)
            if context_terms & text_terms:
                score += 2.5 * len(context_terms & text_terms)
                context_overlap += 1

    if is_definition_query(profile):
        if re.search(
            r"\b(is|means|refers to|defined as|definition|explains?)\b",
            normalized_text,
        ):
            score += 8.0
        else:
            score -= 6.0

    if is_dataset_summary_query(profile):
        if chunk_index is not None and chunk_index <= 1:
            score += 6.0
        heading_matches = len(
            [
                line
                for line in text.splitlines()[:8]
                if _HEADING_CANDIDATE_PATTERN.fullmatch(line.strip())
            ]
        )
        score += heading_matches * 2.0
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and _looks_like_name_line(lines[0]):
            score += 4.0

    if "name" in profile.semantic_tags:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(_looks_like_name_line(line) for line in lines[:3]):
            score += 10.0
        if chunk_index is not None and chunk_index <= 1:
            score += 1.5

    if "contact" in profile.semantic_tags:
        if _EMAIL_PATTERN.search(text):
            score += 5.0
        if _PHONE_PATTERN.search(text):
            score += 4.0

    if "date" in profile.semantic_tags and _DATE_PATTERN.search(text):
        score += 4.5

    if "location" in profile.semantic_tags and re.search(
        r"\b(address|city|country|located|location|place)\b",
        normalized_text,
    ):
        score += 4.0

    line_count = len([line for line in text.splitlines() if line.strip()])
    structured = text.count(":") >= 1 or line_count >= 2
    if is_collection_query(profile) and (
        text.count(":") >= 2 or text.count("*") >= 2 or line_count >= 3
    ):
        score += 2.5

    if is_action_query(profile):
        if re.search(
            r"\b(architected|built|contributed|created|delivered|designed|developed|implemented|integrated|led|optimized|responsibilities|task|tasks|worked)\b",
            normalized_text,
        ):
            score += 7.0
        if context_overlap:
            score += context_overlap * 3.5
        if structured:
            score += 2.5

    if is_comparison_query(profile):
        if context_overlap:
            score += context_overlap * 3.0
        if structured:
            score += 3.0
        if re.search(
            r"\b(another|other|only|outside|prior|previous|current)\b",
            normalized_text,
        ):
            score += 2.0

    if is_entity_context_query(profile):
        if context_overlap:
            score += context_overlap * 4.0
        if re.search(
            r"\b(build|built|contribute|contributed|mention|mentioned|support|supported|use|used|work|worked)\b",
            normalized_text,
        ):
            score += 4.0

    if is_count_query(profile):
        if structured:
            score += 3.0
        if text.count("\n") >= 2 or text.count("•") >= 2 or text.count("*") >= 2:
            score += 2.5

    if profile.attribute_terms:
        if has_strong_intent_signal(text, profile=profile):
            score += 5.5 if is_field_extraction_query(profile) else 3.5
        elif is_collection_query(profile):
            score -= 4.0
        elif is_field_extraction_query(profile):
            score -= 1.5

    if is_boolean_query(profile) and re.search(
        r"\b(yes|no|has|have|had|includes?|contains?|supports?|works?|worked)\b",
        normalized_text,
    ):
        score += 2.0

    if re.search(
        r"\b(backed by|sponsored by|powered by|organized by)\b",
        normalized_text,
    ) and (
        "work" in profile.terms
        or "experience" in profile.terms
        or "employment" in profile.terms
    ):
        score -= 3.0

    return score


def query_focus_hints(profile: QueryProfile) -> list[str]:
    """Return short provider-facing hints about the answer style the query needs."""

    hints: list[str] = []
    if is_dataset_summary_query(profile):
        hints.append(
            "Provide a concise high-level summary of what the attached data contains."
        )
    if is_definition_query(profile):
        hints.append(
            "Only answer if the evidence actually defines or explains the concept."
        )
    if is_boolean_query(profile):
        hints.append(
            "Return a concise yes/no style answer only when the evidence directly supports it."
        )
    if is_action_query(profile):
        hints.append(
            "Summarize the concrete work, responsibilities, or contributions supported by the evidence."
        )
    if is_comparison_query(profile):
        hints.append(
            "Compare the cited evidence carefully before concluding whether there are other matching cases."
        )
    if is_entity_context_query(profile):
        hints.append(
            "Answer only if the referenced entity or topic is explicitly supported within the cited context."
        )
    if is_count_query(profile):
        hints.append(
            "Return a grounded count and mention the counted items when the evidence makes them clear."
        )
    if is_field_extraction_query(profile):
        requested = ", ".join(sorted(profile.attribute_terms))
        hints.append(f"Return only the requested attribute or field: {requested}.")
    if is_collection_query(profile):
        hints.append(
            "Prefer structured lists or enumerated items when the evidence provides them."
        )
    return hints


def has_strong_intent_signal(text: str, *, profile: QueryProfile) -> bool:
    """Return whether one text block strongly matches the requested answer shape."""

    normalized_text = _normalize_text(text)
    intent = primary_intent(profile)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    early_lines = lines[:5]
    heading_like_lines = [line for line in early_lines if _is_heading_only_line(line)]
    normalized_early_lines = [_normalize_text(line) for line in early_lines]
    attribute_in_heading = any(
        attribute in _normalize_text(candidate)
        for candidate in heading_like_lines
        for attribute in profile.attribute_terms
    )
    attribute_in_early_lines = any(
        attribute in normalized_line
        for normalized_line in normalized_early_lines[:3]
        for attribute in profile.attribute_terms
    )
    context_in_text = any(context in normalized_text for context in profile.context_terms)
    structured_lines = [
        line
        for line in early_lines
        if ":" in line
        or line.lstrip().startswith(("-", "*", "•"))
        or (line and line[0].isdigit() and "." in line[:4])
    ]

    if intent == "name":
        return any(_looks_like_name_line(line) for line in lines[:3])
    if intent == "contact":
        return bool(_EMAIL_PATTERN.search(text) or _PHONE_PATTERN.search(text))
    if intent == "date":
        return bool(_DATE_PATTERN.search(text))
    if is_action_query(profile):
        return context_in_text and bool(
            structured_lines
            or re.search(
                r"\b(architected|built|contributed|created|delivered|designed|developed|implemented|integrated|led|optimized|responsibilities|task|tasks|worked)\b",
                normalized_text,
            )
        )
    if is_comparison_query(profile):
        return bool(context_in_text or attribute_in_heading or attribute_in_early_lines) and bool(
            structured_lines or len(early_lines) >= 2
        )
    if is_entity_context_query(profile):
        return context_in_text and bool(
            re.search(
                r"\b(build|built|contribute|contributed|mention|mentioned|support|supported|use|used|work|worked)\b",
                normalized_text,
            )
        )
    if is_count_query(profile):
        return attribute_in_heading or (
            attribute_in_early_lines and bool(structured_lines or len(early_lines) >= 2)
        )
    if is_collection_query(profile):
        if attribute_in_heading:
            return True
        return attribute_in_early_lines and bool(
            structured_lines or len(early_lines) >= 2
        )
    if intent and any(intent in _normalize_text(candidate) for candidate in heading_like_lines):
        return True
    if attribute_in_heading:
        return True
    if attribute_in_early_lines and (
        structured_lines
        or any(":" in line for line in early_lines[:2])
        or len(early_lines) >= 2
    ):
        return True
    if profile.attribute_terms and any(
        attribute in normalized_text for attribute in profile.attribute_terms
    ):
        if is_field_extraction_query(profile):
            return any(":" in line for line in early_lines[:2]) or bool(
                heading_like_lines
            )
        return True
    if is_collection_query(profile) and (
        text.count(":") >= 2 or text.count("*") >= 2 or text.count("\n") >= 2
    ):
        return True
    return False


def build_retrieval_query_text(profile: QueryProfile) -> str:
    """Expand a user query into a retrieval-oriented query string."""

    supplemental_terms: list[str] = [profile.normalized_text]
    supplemental_terms.extend(sorted(profile.attribute_terms))
    supplemental_terms.extend(sorted(profile.context_terms))

    for semantic_tag in sorted(profile.semantic_tags):
        synonyms = sorted(_CANONICAL_ATTRIBUTE_SYNONYMS.get(semantic_tag, set()))
        supplemental_terms.extend(synonyms[:3])

    query_tokens = set(profile.normalized_text.split())
    expanded_only_terms = [
        term
        for term in sorted(profile.expanded_terms)
        if term not in query_tokens and term not in _SUMMARY_QUERY_NOISE
    ]
    supplemental_terms.extend(expanded_only_terms[:6])

    if is_dataset_summary_query(profile):
        supplemental_terms.extend(["overview", "summary", "introduction"])
    if is_definition_query(profile):
        supplemental_terms.extend(["definition", "means", "refers to"])
    if is_collection_query(profile):
        supplemental_terms.extend(["list", "items", "categories"])
    if is_count_query(profile):
        supplemental_terms.extend(["count", "number", "total"])
    if is_action_query(profile):
        supplemental_terms.extend(["responsibilities", "contributions", "tasks"])
    if is_comparison_query(profile):
        supplemental_terms.extend(["compare", "other", "another"])
    if is_entity_context_query(profile):
        supplemental_terms.extend(["mention", "project", "support", "work"])

    deduped_terms: list[str] = []
    seen: set[str] = set()
    for term in supplemental_terms:
        normalized = _normalize_text(term)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_terms.append(term.strip())
    return " ".join(deduped_terms)
