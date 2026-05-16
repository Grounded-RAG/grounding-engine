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
_LOW_SIGNAL_CLAIM_TERMS = {
    "grounded",
    "support",
    "supports",
    "supported",
    "using",
    "uses",
    "system",
}


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


def extract_claims(answer_text: str) -> tuple[str, ...]:
    """Split one answer into simple auditable claims."""

    normalized = re.sub(r"\s*\[[A-Z]\d+\]", "", answer_text).strip()
    if not normalized:
        return ()

    claims = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_PATTERN.split(normalized)
        if sentence.strip()
    ]
    return tuple(claims or [normalized])


def _contains_negation(text: str) -> bool:
    return any(f" {term} " in f" {text} " for term in _NEGATION_TERMS)


def _assess_claim_against_evidence(*, claim: str, evidence_text_by_chunk: dict[str, str]) -> tuple[_EvidenceAssessment, tuple[str, ...]]:
    """Assess one claim against all evidence and return best support plus contradictions."""

    terms = _claim_terms(claim)
    claim_has_negation = _contains_negation(_normalize_text(claim))
    best = _EvidenceAssessment(
        chunk_id="",
        matched_terms=(),
        missing_terms=terms,
        support_score=1.0 if not terms else 0.0,
        contradicts_claim=False,
    )
    contradiction_chunk_ids: list[str] = []

    for chunk_id, evidence_text in evidence_text_by_chunk.items():
        if not terms:
            score = 1.0
            matched_terms = ()
            missing_terms = ()
        else:
            matched_terms = tuple(term for term in terms if term in evidence_text)
            missing_terms = tuple(term for term in terms if term not in matched_terms)
            score = len(matched_terms) / len(terms)

        evidence_has_negation = _contains_negation(evidence_text)
        contradicts = bool(terms) and matched_terms and claim_has_negation != evidence_has_negation

        assessment = _EvidenceAssessment(
            chunk_id=chunk_id,
            matched_terms=matched_terms,
            missing_terms=missing_terms,
            support_score=score,
            contradicts_claim=contradicts,
        )

        if contradicts:
            contradiction_chunk_ids.append(chunk_id)

        if assessment.support_score > best.support_score:
            best = assessment
        elif assessment.support_score == best.support_score:
            # Prefer non-contradicting evidence at the same score.
            if best.contradicts_claim and not assessment.contradicts_claim:
                best = assessment

    return best, tuple(dict.fromkeys(contradiction_chunk_ids))


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

        verified_claims.append(
            VerifiedClaim(
                text=claim,
                status=status,
                matched_chunk_ids=persisted_chunk_ids,
                missing_terms=best_assessment.missing_terms,
                support_score=best_assessment.support_score,
                contradiction_chunk_ids=contradiction_chunk_ids,
            )
        )

    retry_query_text: str | None = None

    if contradiction_detected:
        decision = "degrade"
        reason = "CONTRADICTORY_EVIDENCE"
    elif unsupported_detected:
        decision = "refuse"
        reason = "UNSUPPORTED_CLAIMS"
        retry_terms = [
            term
            for claim in verified_claims
            if claim.status == "unsupported"
            for term in claim.missing_terms
        ]
        if retry_terms:
            retry_query_text = " ".join(dict.fromkeys(retry_terms))
    elif partial_detected or response.verification_status == "degraded":
        decision = "degrade"
        reason = (
            response.degraded_reasons[0]
            if response.degraded_reasons
            else "PARTIAL_SUPPORT"
        )
        retry_terms = [
            term
            for claim in verified_claims
            if claim.status == "partially_supported"
            for term in claim.missing_terms
        ]
        if retry_terms:
            retry_query_text = " ".join(dict.fromkeys(retry_terms))
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
