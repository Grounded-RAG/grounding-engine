"""Shared query analysis helpers for retrieval and grounded answering."""

from __future__ import annotations

import re
from dataclasses import dataclass


_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "does",
    "for",
    "from",
    "give",
    "have",
    "hello",
    "help",
    "how",
    "into",
    "just",
    "me",
    "need",
    "of",
    "on",
    "or",
    "please",
    "show",
    "tell",
    "the",
    "their",
    "them",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
    "would",
    "your",
}

_INTENT_KEYWORDS = {
    "name": {
        "applicant",
        "candidate",
        "contact",
        "fullname",
        "header",
        "name",
        "owner",
        "person",
        "profile",
        "resume",
        "student",
    },
    "contact": {
        "contact",
        "email",
        "github",
        "linkedin",
        "mail",
        "number",
        "phone",
    },
    "education": {
        "academic",
        "college",
        "course",
        "courses",
        "cgpa",
        "degree",
        "education",
        "educational",
        "gpa",
        "school",
        "studies",
        "study",
        "university",
    },
    "experience": {
        "career",
        "employment",
        "experience",
        "intern",
        "job",
        "position",
        "role",
        "roles",
        "work",
        "worked",
    },
    "skills": {
        "framework",
        "frameworks",
        "language",
        "languages",
        "skill",
        "skills",
        "stack",
        "technical",
        "tool",
        "tools",
        "technologies",
    },
    "projects": {
        "build",
        "built",
        "create",
        "created",
        "developed",
        "portfolio",
        "project",
        "projects",
    },
    "awards": {
        "achievement",
        "achievements",
        "award",
        "awards",
        "certificate",
        "certificates",
        "honor",
        "honors",
        "honours",
        "recognition",
    },
}

_INTENT_HEADINGS = {
    "education": {"education", "academic background"},
    "experience": {"experience", "professional experience", "work experience"},
    "skills": {"skills", "technical skills"},
    "projects": {"projects", "project experience"},
    "awards": {"awards", "certificates", "achievements"},
    "contact": {"contact", "contact information"},
}

_NAME_LINE_PATTERN = re.compile(r"^[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){1,4}$")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_DEGREE_PATTERN = re.compile(
    r"\b(bsc|b\.sc|bachelor|msc|m\.sc|master|phd|doctorate|diploma)\b",
    re.IGNORECASE,
)
_ROLE_PATTERN = re.compile(
    r"\b(engineer|developer|intern|manager|researcher|analyst|lead|consultant)\b",
    re.IGNORECASE,
)
_FIELD_EXTRACTION_INTENTS = {"name", "contact", "education", "experience", "skills"}
_DEFINITION_QUERY_PATTERN = re.compile(
    r"^(?:what\s+(?:is|does)\s+.+?\s+(?:mean|means)\??|define\s+.+)$"
)
_BOOLEAN_QUERY_PATTERN = re.compile(
    r"^(?:is|are|was|were|do|does|did|has|have|had|can)\b"
)


@dataclass(frozen=True)
class QueryProfile:
    """Normalized query understanding shared by retrieval and answering."""

    raw_text: str
    normalized_text: str
    terms: frozenset[str]
    expanded_terms: frozenset[str]
    intents: frozenset[str]


def _normalize_token(token: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", token.casefold())
    if normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return normalized


def _normalize_text(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", text.casefold())
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_meaningful_terms(text: str) -> set[str]:
    """Return normalized non-trivial terms from free text."""

    return {
        normalized
        for token in re.findall(r"[A-Za-z0-9]+", text)
        if (normalized := _normalize_token(token))
        and len(normalized) >= 3
        and normalized not in _STOPWORDS
    }


def build_query_profile(query_text: str) -> QueryProfile:
    """Build one reusable query profile from the user's text."""

    normalized_text = _normalize_text(query_text)
    terms = tokenize_meaningful_terms(query_text)
    intents = {
        intent
        for intent, keywords in _INTENT_KEYWORDS.items()
        if keywords & terms or any(phrase in normalized_text for phrase in keywords if " " in phrase)
    }
    expanded_terms = set(terms)
    for intent in intents:
        expanded_terms.update(_INTENT_KEYWORDS[intent])
        expanded_terms.update(_INTENT_HEADINGS.get(intent, set()))

    return QueryProfile(
        raw_text=query_text,
        normalized_text=normalized_text,
        terms=frozenset(terms),
        expanded_terms=frozenset(expanded_terms),
        intents=frozenset(intents),
    )


def is_definition_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a definition or explanation."""

    return bool(_DEFINITION_QUERY_PATTERN.match(profile.normalized_text))


def is_boolean_query(profile: QueryProfile) -> bool:
    """Return whether the query is asking for a yes/no style answer."""

    return bool(_BOOLEAN_QUERY_PATTERN.match(profile.normalized_text))


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

    if profile.intents & _INTENT_HEADINGS.keys():
        heading_candidates = [line.strip() for line in text.splitlines() if line.strip()][:2]
        for intent in profile.intents:
            headings = _INTENT_HEADINGS.get(intent, set())
            if any(heading in _normalize_text(candidate) for heading in headings for candidate in heading_candidates):
                score += 6.0

    if is_definition_query(profile):
        if re.search(r"\b(is|means|refers to|defined as|definition)\b", normalized_text):
            score += 8.0
        else:
            score -= 6.0

    if "name" in profile.intents:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(_NAME_LINE_PATTERN.match(line) for line in lines[:3]):
            score += 10.0
        if chunk_index is not None and chunk_index <= 1:
            score += 1.5

    if "contact" in profile.intents:
        if _EMAIL_PATTERN.search(text):
            score += 5.0
        if _PHONE_PATTERN.search(text):
            score += 4.0

    if "education" in profile.intents and _DEGREE_PATTERN.search(text):
        score += 6.5

    if "experience" in profile.intents and _ROLE_PATTERN.search(text):
        score += 6.0
    if "experience" in profile.intents and re.search(r"\b(present|intern|labs|company)\b", normalized_text):
        score += 2.5

    if "skills" in profile.intents:
        if "technical skills" in normalized_text:
            score += 8.0
        elif normalized_text.startswith("skills"):
            score += 6.0
        elif "skills" in normalized_text:
            score += 1.5
        if text.count(":") >= 2 or text.count("•") >= 2:
            score += 2.0
        if "enhanced skills" in normalized_text:
            score -= 2.5

    if "projects" in profile.intents and "project" in normalized_text:
        score += 4.0

    if "awards" in profile.intents and re.search(r"\b(award|awarded|honoree|winner|certificate)\b", normalized_text):
        score += 4.0

    if is_boolean_query(profile) and "worked" in profile.normalized_text:
        if re.search(r"\b(work|worked|experience|employment|role|intern|engineer|developer)\b", normalized_text):
            score += 3.5
        if re.search(r"\b(backed by|sponsored by)\b", normalized_text):
            score -= 2.5

    return score


def query_focus_hints(profile: QueryProfile) -> list[str]:
    """Return short provider-facing hints about the answer style the query needs."""

    hints: list[str] = []
    if "name" in profile.intents:
        hints.append("Extract the person's exact name if the evidence contains it.")
    if "contact" in profile.intents:
        hints.append("Return only the requested contact field, not unrelated profile details.")
    if "education" in profile.intents:
        hints.append("Prefer the education section or degree line over unrelated achievements.")
    if "experience" in profile.intents:
        hints.append("Prefer roles, companies, and work history over awards or projects.")
    if "skills" in profile.intents:
        hints.append("Prefer the skills section or skill-category lines over incidental uses of the word skills.")
    if "projects" in profile.intents:
        hints.append("Prefer named projects and what was built.")
    if "awards" in profile.intents:
        hints.append("Prefer recognitions, honors, awards, and certificates.")
    if is_definition_query(profile):
        hints.append("Only answer if the evidence actually defines or explains the concept.")
    if is_boolean_query(profile):
        hints.append("Return a concise yes/no style answer only when the evidence directly supports it.")
    return hints


def primary_intent(profile: QueryProfile) -> str | None:
    """Return the dominant field-like intent when one exists."""

    for intent in (
        "name",
        "contact",
        "education",
        "experience",
        "skills",
        "projects",
        "awards",
    ):
        if intent in profile.intents:
            return intent
    return None


def is_field_extraction_query(profile: QueryProfile) -> bool:
    """Return whether the query asks for one focused field rather than open summarization."""

    return bool(profile.intents & _FIELD_EXTRACTION_INTENTS)


def has_strong_intent_signal(text: str, *, profile: QueryProfile) -> bool:
    """Return whether one text block strongly matches the primary query intent."""

    normalized_text = _normalize_text(text)
    intent = primary_intent(profile)
    if intent is None:
        return False

    if intent == "name":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return any(_NAME_LINE_PATTERN.match(line) for line in lines[:3])
    if intent == "contact":
        return bool(_EMAIL_PATTERN.search(text) or _PHONE_PATTERN.search(text))
    if intent == "education":
        return "education" in normalized_text or bool(_DEGREE_PATTERN.search(text))
    if intent == "experience":
        return "experience" in normalized_text or bool(_ROLE_PATTERN.search(text))
    if intent == "skills":
        return (
            "technical skills" in normalized_text
            or normalized_text.startswith("skills")
            or text.count(":") >= 2
            or text.count("•") >= 2
        )
    return False


def build_retrieval_query_text(profile: QueryProfile) -> str:
    """Expand a user query into a retrieval-oriented query string."""

    supplemental_terms: list[str] = []
    for intent in sorted(profile.intents):
        keywords = sorted(_INTENT_KEYWORDS.get(intent, set()))
        headings = sorted(_INTENT_HEADINGS.get(intent, set()))
        supplemental_terms.extend(headings[:2])
        supplemental_terms.extend(keywords[:2] if is_field_extraction_query(profile) else keywords[:4])

    if "name" in profile.intents:
        supplemental_terms.extend(["full name", "profile header"])
    if "contact" in profile.intents:
        supplemental_terms.extend(["contact information"])
    if is_definition_query(profile):
        supplemental_terms.extend(["definition", "means", "refers to"])

    deduped_terms: list[str] = []
    seen: set[str] = set()
    for term in [profile.raw_text, *supplemental_terms]:
        normalized = _normalize_text(term)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_terms.append(term.strip())
    return " ".join(deduped_terms)
