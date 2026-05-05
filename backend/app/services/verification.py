"""Critical-tier verification helpers for grounded answers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.pipeline.contracts import EvidencePackage
from app.schemas.query import GroundedAnswerResponse


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_NEGATION_TERMS = {"not", "no", "never", "without", "cannot", "cant", "doesnt", "isnt"}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class VerifiedClaim:
    """One auditable claim and its support classification."""

    text: str
    status: str
    matched_chunk_ids: tuple[str, ...]
    missing_terms: tuple[str, ...]


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
    contradiction_detected: bool = False
    bounded_correction_attempted: bool = False


def _normalize_text(value: str) -> str:
    """Normalize free text for simple lexical support checks."""

    return _WHITESPACE_PATTERN.sub(" ", value.casefold()).strip()


def _claim_terms(claim_text: str) -> tuple[str, ...]:
    """Extract the meaningful lexical terms for one claim."""

    terms: list[str] = []
    for token in _TOKEN_PATTERN.findall(_normalize_text(claim_text)):
        if len(token) < 3 or token in _STOPWORDS:
            continue
        if token not in terms:
            terms.append(token)
    return tuple(terms)


def extract_claims(answer_text: str) -> tuple[str, ...]:
    """Split one answer into simple auditable claims."""

    normalized = answer_text.strip()
    if not normalized:
        return ()

    claims = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_PATTERN.split(normalized)
        if sentence.strip()
    ]
    return tuple(claims or [normalized])


def _detect_contradiction(
    *,
    claims: tuple[str, ...],
    evidence_text_by_chunk: dict[str, str],
) -> bool:
    """Detect simple support conflicts across evidence for the same claim terms."""

    if len(evidence_text_by_chunk) < 2:
        return False

    claim_terms = {
        term
        for claim in claims
        for term in _claim_terms(claim)
    }
    if not claim_terms:
        return False

    chunk_texts = list(evidence_text_by_chunk.values())
    has_affirming = False
    has_negating = False

    for evidence_text in chunk_texts:
        if not any(term in evidence_text for term in claim_terms):
            continue
        contains_negation = any(f" {term} " in f" {evidence_text} " for term in _NEGATION_TERMS)
        if contains_negation:
            has_negating = True
        else:
            has_affirming = True
        if has_affirming and has_negating:
            return True

    return False


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
    contradiction_detected = _detect_contradiction(
        claims=claims,
        evidence_text_by_chunk=evidence_text_by_chunk,
    )

    verified_claims: list[VerifiedClaim] = []
    unsupported_detected = False
    partial_detected = False
    supported_claim_count = 0
    partially_supported_claim_count = 0
    unsupported_claim_count = 0

    for claim in claims:
        terms = _claim_terms(claim)
        matched_chunk_ids: list[str] = []
        missing_terms = list(terms)

        if terms:
            for chunk_id, evidence_text in evidence_text_by_chunk.items():
                present_terms = [term for term in terms if term in evidence_text]
                if not present_terms:
                    continue
                matched_chunk_ids.append(chunk_id)
                missing_terms = [term for term in missing_terms if term not in present_terms]

        if not terms:
            status = "supported"
            supported_claim_count += 1
        elif not matched_chunk_ids:
            status = "unsupported"
            unsupported_detected = True
            unsupported_claim_count += 1
        elif missing_terms:
            status = "partially_supported"
            partial_detected = True
            partially_supported_claim_count += 1
        else:
            status = "supported"
            supported_claim_count += 1

        verified_claims.append(
            VerifiedClaim(
                text=claim,
                status=status,
                matched_chunk_ids=tuple(matched_chunk_ids),
                missing_terms=tuple(missing_terms),
            )
        )

    if contradiction_detected:
        decision = "degrade"
        reason = "CONTRADICTORY_EVIDENCE"
    elif unsupported_detected:
        decision = "refuse"
        reason = "UNSUPPORTED_CLAIMS"
    elif partial_detected or response.verification_status == "degraded":
        decision = "degrade"
        reason = (
            response.degraded_reasons[0]
            if response.degraded_reasons
            else "PARTIAL_SUPPORT"
        )
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
        contradiction_detected=contradiction_detected,
    )
