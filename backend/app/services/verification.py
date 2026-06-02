"""Critical-tier verification helpers for grounded answers."""

from __future__ import annotations

import re
from dataclasses import dataclass


from app.core.flags import is_semantic_verification_enabled
from app.pipeline.contracts import EvidencePackage
from app.schemas.query import GroundedAnswerResponse


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_WORD_BOUNDARY_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}

# Abbreviations that must stay attached to the following word(s) when they
# end a sentence fragment. These are tokens that *require* a continuation
# (a name for a title, a clarification for "i.e.", etc.) so a stray split
# on the period produces a broken claim. Initials like "U.S." are NOT
# in this set because they are a complete term and split correctly.
_FORCED_CONTINUATION_ABBREVIATIONS = frozenset(
    {
        "dr",
        "mr",
        "ms",
        "mrs",
        "prof",
        "sr",
        "jr",
        "st",
        "rev",
        "e.g",
        "i.e",
        "a.m",
        "p.m",
    }
)

# Negation words for contradiction detection.
_NEGATION_TERMS = {"not", "no", "never", "without", "cannot", "cant", "doesnt", "isnt", "wont", "hasnt", "havent", "didnt", "arent", "wasnt", "werent"}

# Antonym pairs — if a claim contains one side and evidence contains the other
# (or vice versa), the evidence contradicts the claim.
_ANTONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("available", "unavailable"),
    ("supported", "unsupported"),
    ("enabled", "disabled"),
    ("allowed", "blocked"),
    ("allowed", "denied"),
    ("present", "absent"),
    ("include", "exclude"),
    ("includes", "excludes"),
    ("exists", "missing"),
    ("active", "inactive"),
    ("online", "offline"),
    ("open", "closed"),
    ("public", "private"),
    ("required", "optional"),
    ("valid", "invalid"),
    ("success", "failure"),
    ("succeeds", "fails"),
    ("pass", "fail"),
    ("passes", "fails"),
    ("yes", "no"),
    ("true", "false"),
    ("can", "cannot"),
    ("can", "cant"),
    ("will", "wont"),
    ("has", "hasnt"),
    ("have", "havent"),
    ("is", "isnt"),
    ("are", "arent"),
    ("was", "wasnt"),
    ("were", "werent"),
    ("did", "didnt"),
    ("does", "doesnt"),
    ("do", "dont"),
)

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "with",
}
_LOW_SIGNAL_CLAIM_TERMS = {
    "grounded", "support", "supports", "supported", "using", "uses", "system",
}
_RETRY_TERM_PRIORITY = {
    "supported", "supports", "export", "exports", "offline", "online",
    "upload", "uploads", "tenant", "safe",
}

# Morphological suffix stripping — order matters: longest first.
_MORPH_SUFFIXES = ("tion", "ing", "tion", "ers", "ed", "es", "er", "ly", "s")


def _morph_root(term: str) -> str:
    """Strip common English suffixes to approximate the root form."""
    if len(term) <= 4:
        return term
    for suffix in _MORPH_SUFFIXES:
        if term.endswith(suffix) and len(term) - len(suffix) >= 3:
            return term[: -len(suffix)]
    return term


def _word_boundary_pattern(term: str) -> re.Pattern[str]:
    """Return a compiled word-boundary regex for one term, cached."""
    if term not in _WORD_BOUNDARY_PATTERN_CACHE:
        _WORD_BOUNDARY_PATTERN_CACHE[term] = re.compile(
            r"\b" + re.escape(term) + r"\b"
        )
    return _WORD_BOUNDARY_PATTERN_CACHE[term]


def _term_in_text(term: str, text: str) -> bool:
    """Return True if *term* appears as a whole word in *text*.

    Falls back to morphological root matching when the exact form is absent.
    Uses word-boundary regex instead of plain substring to avoid false positives
    (e.g. "port" matching "export").
    """
    if _word_boundary_pattern(term).search(text):
        return True
    root = _morph_root(term)
    if root != term and len(root) >= 3:
        return bool(_word_boundary_pattern(root).search(text))
    return False


def _find_term_position(term: str, text: str) -> int:
    """Return the first character position of *term* in *text* as a whole
    word, falling back to the morphological root. Returns -1 if neither is
    present. The morph fallback is required for the negation-proximity
    check: ``str.find`` returns -1 for morph-only matches and would
    otherwise force the proximity comparison to use a sentinel value.
    """
    match = _word_boundary_pattern(term).search(text)
    if match is not None:
        return match.start()
    root = _morph_root(term)
    if root != term and len(root) >= 3:
        match = _word_boundary_pattern(root).search(text)
        if match is not None:
            return match.start()
    return -1


def _extract_bigrams(terms: tuple[str, ...]) -> tuple[str, ...]:
    """Return consecutive 2-word phrases from a term sequence."""
    return tuple(f"{terms[i]} {terms[i + 1]}" for i in range(len(terms) - 1))


def _normalize_text(value: str) -> str:
    """Normalize free text for support checks."""
    return _WHITESPACE_PATTERN.sub(" ", value.casefold()).strip()


def _claim_terms(claim_text: str) -> tuple[str, ...]:
    """Extract the meaningful lexical terms for one claim."""
    terms: list[str] = []
    for token in _TOKEN_PATTERN.findall(_normalize_text(claim_text)):
        if (
            len(token) < 3
            or token in _STOPWORDS
            or token in _LOW_SIGNAL_CLAIM_TERMS
            or re.fullmatch(r"e\d+", token)
        ):
            continue
        if token not in terms:
            terms.append(token)
    return tuple(terms)


def _rank_retry_terms(*, claims: tuple[VerifiedClaim, ...]) -> tuple[str, ...]:
    """Return a stable retry query focused on missing high-signal claim terms."""
    ranked_terms: list[str] = []
    for claim in claims:
        if claim.status not in {"unsupported", "partially_supported"}:
            continue
        claim_terms = _claim_terms(claim.text)
        for term in claim_terms:
            if term in claim.missing_terms and term not in ranked_terms:
                ranked_terms.append(term)
        for term in claim.missing_terms:
            if term not in ranked_terms:
                ranked_terms.append(term)

    prioritized = [term for term in ranked_terms if term in _RETRY_TERM_PRIORITY]
    remaining = [term for term in ranked_terms if term not in _RETRY_TERM_PRIORITY]
    return tuple(prioritized + remaining)


def _ends_with_forced_continuation(sentence: str) -> bool:
    """Return True if `sentence` ends with a known abbreviation that requires
    a continuation (e.g. ``Dr.`` expects a name, ``i.e.`` expects a clause).
    """
    stripped = sentence.rstrip()
    if not stripped or not stripped.endswith("."):
        return False
    last_token = stripped.split()[-1]
    return last_token.rstrip(".").lower() in _FORCED_CONTINUATION_ABBREVIATIONS


def _split_sentences_preserving_abbreviations(text: str) -> list[str]:
    """Split `text` on sentence-final punctuation while keeping known
    abbreviations attached to the following fragment. This avoids the
    common false split of ``Dr. Smith said X.`` into ``['Dr.', 'Smith said X.']``.
    """
    raw = [s.strip() for s in _SENTENCE_SPLIT_PATTERN.split(text) if s.strip()]
    if not raw:
        return [text.strip()] if text.strip() else []

    merged: list[str] = []
    buffer: str | None = None
    for sentence in raw:
        candidate = f"{buffer} {sentence}".strip() if buffer is not None else sentence
        if _ends_with_forced_continuation(candidate):
            buffer = candidate
            continue
        merged.append(candidate)
        buffer = None
    if buffer is not None:
        merged.append(buffer)
    return merged


def extract_claims(answer_text: str) -> tuple[str, ...]:
    """Split one answer into simple auditable claims."""
    normalized = re.sub(r"\s*\[[A-Z]\d+\]", "", answer_text).strip()
    if not normalized:
        return ()

    claims = _split_sentences_preserving_abbreviations(normalized)
    return tuple(claims or [normalized])


def _contains_negation(text: str) -> bool:
    return any(_word_boundary_pattern(term).search(text) for term in _NEGATION_TERMS)


def _extract_numbers(text: str) -> set[str]:
    """Return all numeric tokens from text (integers and simple decimals)."""
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def _antonym_contradiction(claim_norm: str, evidence_norm: str) -> bool:
    """Return True when claim and evidence carry semantically opposite polarity.

    Checks two things:
    1. Antonym pairs — one side is in the claim, the other in the evidence.
    2. Numeric contradiction — both texts share a numeric context but with
       different values (e.g., claim says "5 items", evidence says "10 items").
    """
    for word_a, word_b in _ANTONYM_PAIRS:
        claim_has_a = bool(_word_boundary_pattern(word_a).search(claim_norm))
        claim_has_b = bool(_word_boundary_pattern(word_b).search(claim_norm))
        evidence_has_a = bool(_word_boundary_pattern(word_a).search(evidence_norm))
        evidence_has_b = bool(_word_boundary_pattern(word_b).search(evidence_norm))

        if (claim_has_a and evidence_has_b and not evidence_has_a) or (
            claim_has_b and evidence_has_a and not evidence_has_b
        ):
            return True

    # Numeric contradiction: both texts have numbers but they differ.
    claim_numbers = _extract_numbers(claim_norm)
    evidence_numbers = _extract_numbers(evidence_norm)
    if claim_numbers and evidence_numbers and claim_numbers.isdisjoint(evidence_numbers):
        # Only flag as contradiction if there is meaningful term overlap
        # (i.e., they are talking about the same thing).
        claim_terms_set = set(_TOKEN_PATTERN.findall(claim_norm)) - _STOPWORDS
        evidence_terms_set = set(_TOKEN_PATTERN.findall(evidence_norm)) - _STOPWORDS
        shared = claim_terms_set & evidence_terms_set
        if len(shared) >= 2:
            return True

    return False


@dataclass(frozen=True)
class VerifiedClaim:
    """One auditable claim and its support classification."""

    text: str
    status: str
    matched_chunk_ids: tuple[str, ...]
    missing_terms: tuple[str, ...]
    support_score: float
    contradiction_chunk_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerifierResult:
    """Structured verification result for the Critical path."""

    decision: str
    reason: str | None
    claims: tuple[VerifiedClaim, ...]
    unsupported_claims_detected: bool
    supported_claim_count: int = 0
    partially_supported_claim_count: int = 0
    unsupported_claim_count: int = 0
    contradicted_claim_count: int = 0
    retry_query_text: str | None = None
    contradiction_detected: bool = False
    bounded_correction_attempted: bool = False


@dataclass(frozen=True)
class _EvidenceAssessment:
    chunk_id: str
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    support_score: float
    contradicts_claim: bool


def _assess_claim_against_evidence_semantic(
    *,
    claim: str,
    evidence_text_by_chunk: dict[str, str],
) -> tuple[_EvidenceAssessment, tuple[str, ...]]:
    """Assess one claim using word-boundary + morphological + bigram matching.

    Improvements over the previous lexical version:
    - Word-boundary regex prevents substring false positives ("port" in "export").
    - Morphological root matching catches "support"/"supports"/"supported" together.
    - Bigram phrase matching boosts score when multi-word sequences match exactly.
    - Antonym-pair contradiction catches semantic polarity flips.
    - Numeric contradiction catches value mismatches in the same context.
    - Negation-proximity check: negation only counts when it is near matched terms.
    - CRAG union: matched terms are unioned across all chunks so a claim whose
      terms are spread across multiple chunks is not wrongly refused.
    """
    terms = _claim_terms(claim)
    bigrams = _extract_bigrams(terms)
    claim_norm = _normalize_text(claim)
    claim_has_negation = _contains_negation(claim_norm)

    best_score = -1.0
    best_chunk_id = ""
    best_contradicts = False
    union_matched: set[str] = set()
    union_bigram_matches = 0
    contradiction_chunk_ids: list[str] = []

    for chunk_id, evidence_text in evidence_text_by_chunk.items():
        if not terms:
            score = 1.0
            matched_terms: tuple[str, ...] = ()
        else:
            matched_terms = tuple(
                term for term in terms if _term_in_text(term, evidence_text)
            )
            base_score = len(matched_terms) / len(terms)

            # Bigram bonus: each matching bigram phrase lifts the score slightly.
            bigram_matches = sum(
                1 for bg in bigrams if bg in evidence_text
            )
            bigram_bonus = (bigram_matches / max(len(bigrams), 1)) * 0.15 if bigrams else 0.0
            score = min(1.0, base_score + bigram_bonus)

        evidence_norm = evidence_text
        evidence_has_negation = _contains_negation(evidence_norm)

        # Contradiction logic (three layers):
        # 1. Antonym-pair or numeric polarity flip.
        # 2. Negation-flip: negation presence differs AND there are matched terms
        #    (so we know both texts discuss the same subject).
        antonym_contradicts = bool(terms) and matched_terms and _antonym_contradiction(
            claim_norm, evidence_norm
        )
        negation_contradicts = (
            bool(terms)
            and bool(matched_terms)
            and claim_has_negation != evidence_has_negation
            # Require the negation to be "near" a matched term (within 40 chars).
            # Use the morph-aware position lookup so morph-only matches are not
            # silently dropped from the proximity test.
            and any(
                any(
                    abs(m.start() - _find_term_position(term, evidence_norm)) < 40
                    for term in matched_terms
                )
                for neg in _NEGATION_TERMS
                for m in [_word_boundary_pattern(neg).search(evidence_norm)]
                if m
            )
        )
        contradicts = antonym_contradicts or negation_contradicts

        if contradicts:
            contradiction_chunk_ids.append(chunk_id)

        # Track union semantics for the global score and retry query.
        union_matched.update(matched_terms)
        union_bigram_matches += sum(1 for bg in bigrams if bg in evidence_text)

        # Best chunk is the highest-scoring single chunk; kept for provenance
        # (the persisted_chunk_ids trace) and to prefer non-contradicting chunks.
        if score > best_score or (
            score == best_score and best_contradicts and not contradicts
        ):
            best_score = score
            best_chunk_id = chunk_id
            best_contradicts = contradicts

    if not evidence_text_by_chunk:
        return _EvidenceAssessment(
            chunk_id="",
            matched_terms=(),
            missing_terms=terms,
            support_score=1.0 if not terms else 0.0,
            contradicts_claim=False,
        ), ()

    # CRAG union: a term is "matched" if it appears in any chunk. The chunk_id
    # of the highest-scoring chunk is preserved for trace purposes.
    if not terms:
        union_score = 1.0
        global_missing: tuple[str, ...] = ()
    else:
        global_missing = tuple(term for term in terms if term not in union_matched)
        base_score = len(union_matched) / len(terms)
        bigram_bonus = (
            (union_bigram_matches / max(len(bigrams), 1)) * 0.15
            if bigrams
            else 0.0
        )
        union_score = min(1.0, base_score + bigram_bonus)

    best = _EvidenceAssessment(
        chunk_id=best_chunk_id,
        matched_terms=tuple(union_matched),
        missing_terms=global_missing,
        support_score=union_score,
        contradicts_claim=best_contradicts,
    )

    return best, tuple(dict.fromkeys(contradiction_chunk_ids))


def _assess_claim_against_evidence_lexical(
    *,
    claim: str,
    evidence_text_by_chunk: dict[str, str],
) -> tuple[_EvidenceAssessment, tuple[str, ...]]:
    """Legacy lexical assessment kept for A/B comparison and fallback.

    Uses CRAG union semantics: a term is considered matched if it appears
    in any chunk. The best single chunk id is preserved for provenance.
    """
    terms = _claim_terms(claim)
    claim_has_negation = _contains_negation(_normalize_text(claim))

    best_score = -1.0
    best_chunk_id = ""
    best_contradicts = False
    union_matched: set[str] = set()
    contradiction_chunk_ids: list[str] = []

    for chunk_id, evidence_text in evidence_text_by_chunk.items():
        if not terms:
            score = 1.0
            matched_terms: tuple[str, ...] = ()
        else:
            matched_terms = tuple(term for term in terms if term in evidence_text)
            score = len(matched_terms) / len(terms)

        evidence_has_negation = _contains_negation(evidence_text)
        contradicts = bool(terms) and bool(matched_terms) and claim_has_negation != evidence_has_negation

        if contradicts:
            contradiction_chunk_ids.append(chunk_id)

        union_matched.update(matched_terms)

        if score > best_score or (
            score == best_score and best_contradicts and not contradicts
        ):
            best_score = score
            best_chunk_id = chunk_id
            best_contradicts = contradicts

    if not evidence_text_by_chunk:
        return _EvidenceAssessment(
            chunk_id="",
            matched_terms=(),
            missing_terms=terms,
            support_score=1.0 if not terms else 0.0,
            contradicts_claim=False,
        ), ()

    if not terms:
        global_score = 1.0
        global_missing: tuple[str, ...] = ()
    else:
        global_missing = tuple(term for term in terms if term not in union_matched)
        global_score = len(union_matched) / len(terms)

    best = _EvidenceAssessment(
        chunk_id=best_chunk_id,
        matched_terms=tuple(union_matched),
        missing_terms=global_missing,
        support_score=global_score,
        contradicts_claim=best_contradicts,
    )

    return best, tuple(dict.fromkeys(contradiction_chunk_ids))


def _assess_claim_against_evidence(
    *,
    claim: str,
    evidence_text_by_chunk: dict[str, str],
) -> tuple[_EvidenceAssessment, tuple[str, ...]]:
    """Route to semantic or lexical assessment based on the feature flag."""
    if is_semantic_verification_enabled():
        return _assess_claim_against_evidence_semantic(
            claim=claim,
            evidence_text_by_chunk=evidence_text_by_chunk,
        )
    return _assess_claim_against_evidence_lexical(
        claim=claim,
        evidence_text_by_chunk=evidence_text_by_chunk,
    )


def verify_critical_response(
    *,
    response: GroundedAnswerResponse,
    evidence_package: EvidencePackage,
) -> VerifierResult:
    """Verify one grounded response against the currently selected evidence package."""
    claims = extract_claims(response.answer)
    evidence_text_by_chunk = {
        item.chunk_id: _normalize_text(item.text)
        for item in evidence_package.items
    }

    verified_claims: list[VerifiedClaim] = []
    unsupported_detected = False
    partial_detected = False
    contradiction_detected = False
    supported_claim_count = 0
    partially_supported_claim_count = 0
    unsupported_claim_count = 0
    contradicted_claim_count = 0

    for claim in claims:
        terms = _claim_terms(claim)
        best_assessment, contradiction_chunk_ids = _assess_claim_against_evidence(
            claim=claim,
            evidence_text_by_chunk=evidence_text_by_chunk,
        )

        if contradiction_chunk_ids:
            status = "contradicted"
            contradiction_detected = True
            contradicted_claim_count += 1
        elif not terms:
            status = "supported"
            supported_claim_count += 1
        elif best_assessment.support_score >= 0.85:
            status = "supported"
            supported_claim_count += 1
        elif best_assessment.support_score >= 0.5:
            status = "partially_supported"
            partial_detected = True
            partially_supported_claim_count += 1
        else:
            status = "unsupported"
            unsupported_detected = True
            unsupported_claim_count += 1

        persisted_chunk_ids = ()
        if best_assessment.chunk_id and status in {"supported", "partially_supported"}:
            persisted_chunk_ids = (best_assessment.chunk_id,)

        # Contradicted claims carry the contradiction chunk IDs for trace clarity.
        trace_chunk_ids = (
            contradiction_chunk_ids if status == "contradicted" else persisted_chunk_ids
        )

        verified_claims.append(
            VerifiedClaim(
                text=claim,
                status=status,
                matched_chunk_ids=trace_chunk_ids,
                missing_terms=best_assessment.missing_terms,
                support_score=best_assessment.support_score,
                contradiction_chunk_ids=contradiction_chunk_ids,
            )
        )

    retry_query_text: str | None = None

    if contradiction_detected:
        decision = "degrade"
        reason = "CONTRADICTORY_EVIDENCE"
        retry_terms = _rank_retry_terms(claims=tuple(verified_claims))
        if retry_terms:
            retry_query_text = " ".join(retry_terms)
    elif unsupported_detected:
        decision = "refuse"
        reason = "UNSUPPORTED_CLAIMS"
        retry_terms = _rank_retry_terms(claims=tuple(verified_claims))
        if retry_terms:
            retry_query_text = " ".join(retry_terms)
    elif partial_detected or response.verification_status == "degraded":
        decision = "degrade"
        reason = (
            response.degraded_reasons[0]
            if response.degraded_reasons
            else "PARTIAL_SUPPORT"
        )
        retry_terms = _rank_retry_terms(claims=tuple(verified_claims))
        if retry_terms:
            retry_query_text = " ".join(retry_terms)
    else:
        decision = "accept"
        reason = None

    return VerifierResult(
        decision=decision,
        reason=reason,
        claims=tuple(verified_claims),
        unsupported_claims_detected=unsupported_detected,
        supported_claim_count=supported_claim_count,
        partially_supported_claim_count=partially_supported_claim_count,
        unsupported_claim_count=unsupported_claim_count,
        contradicted_claim_count=contradicted_claim_count,
        retry_query_text=retry_query_text,
        contradiction_detected=contradiction_detected,
    )

