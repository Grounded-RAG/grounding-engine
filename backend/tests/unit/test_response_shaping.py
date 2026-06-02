"""Unit tests for structured response shaping."""

from __future__ import annotations

import uuid

import pytest

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
from app.services.response_shaping import (
    ResponseShapingError,
    _calculate_confidence,
    shape_degraded_response,
    shape_grounded_response,
)


def _evidence_item(
    *,
    citation_id: str,
    chunk_id: str,
    text: str,
    score: float,
) -> EvidenceItem:
    return EvidenceItem(
        citation_id=citation_id,
        chunk_id=chunk_id,
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        text=text,
        score=score,
        sources=("dense", "sparse"),
    )


def test_shape_grounded_response_builds_structured_citations() -> None:
    """Response shaping should return a structured answer with ordered citations."""

    first = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Grounded supports tenant-safe uploads.",
        score=0.9,
    )
    second = _evidence_item(
        citation_id="E002",
        chunk_id="chunk-2",
        text="It also tracks ingestion job status.",
        score=0.8,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[first, second],
    )
    draft = GroundedAnswerDraft(
        answer_text=(
            "Grounded supports tenant-safe uploads. [E001] "
            "It also tracks ingestion job status. [E002]"
        ),
        cited_evidence_ids=["chunk-1", "chunk-2"],
        citation_snippets={
            "chunk-1": "Grounded supports tenant-safe uploads.",
            "chunk-2": "It also tracks ingestion job status.",
        },
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.answer == draft.answer_text
    assert response.verification_status == "passed"
    assert response.confidence_score == 1.0
    assert response.confidence_label == "high"
    assert response.support_summary == "grounded"
    assert response.degraded_reasons == []
    assert response.provider_backend == "local_grounded_v1"
    assert response.provider_fallback_used is False
    assert [citation.citation_id for citation in response.citations] == ["E001", "E002"]
    assert response.citations[0].quote == "Grounded supports tenant-safe uploads."


def test_shape_grounded_response_deduplicates_repeated_citations() -> None:
    """Repeated cited chunk ids should only appear once in the final response."""

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Grounded returns cited answers.",
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded returns cited answers. [E001] [E001]",
        cited_evidence_ids=["chunk-1", "chunk-1"],
        citation_snippets={"chunk-1": "Grounded returns cited answers."},
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert len(response.citations) == 1
    assert response.citations[0].chunk_id == "chunk-1"


def test_shape_grounded_response_rejects_unknown_evidence_reference() -> None:
    """Drafts that cite unknown chunk ids should fail cleanly."""

    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded uses evidence packaging.",
                score=0.7,
            )
        ],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded uses evidence packaging. [E999]",
        cited_evidence_ids=["chunk-missing"],
        citation_snippets={"chunk-missing": "Grounded uses evidence packaging."},
        generator_provider="local-grounded-v1",
    )

    with pytest.raises(ResponseShapingError, match="unknown evidence chunk"):
        shape_grounded_response(draft=draft, evidence_package=package)


def test_shape_degraded_response_returns_structured_fallback() -> None:
    """Degraded responses should use the same answer schema with explicit reasons."""

    response = shape_degraded_response(
        reason="NO_GROUNDED_EVIDENCE",
        answer_text="I could not find grounded evidence for this query.",
    )

    assert response.answer == "I could not find grounded evidence for this query."
    assert response.citations == []
    assert response.confidence_score == 0.0
    assert response.verification_status == "degraded"
    assert response.degraded_reasons == ["NO_GROUNDED_EVIDENCE"]


def test_shape_grounded_response_degrades_low_confidence_support() -> None:
    """Weak support should still return the answer but mark it degraded."""

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="One weakly ranked supporting snippet.",
        score=0.001,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2", "chunk-3"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="One weakly ranked supporting snippet. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": "One weakly ranked supporting snippet."},
        generator_provider="local-grounded-v1",
        support_coverage=0.2,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.verification_status == "degraded"
    assert response.degraded_reasons == ["LOW_CONFIDENCE_SUPPORT"]
    assert response.confidence_score < 0.25
    assert response.confidence_label == "low"
    assert response.support_summary == "insufficient"


def test_shape_grounded_response_trims_long_citation_quotes() -> None:
    """Citation quotes should stay compact enough for the inspector UI."""

    long_sentence = (
        "Grounded keeps evidence traceable across retrieval, packaging, generation, and product inspection "
        "so reviewers can inspect why a specific answer was returned and whether the support was actually strong enough."
    )
    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text=long_sentence,
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text=f"{long_sentence} [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": long_sentence},
        generator_provider="local-grounded-v1:fallback_from_gemini_v1",
        support_coverage=1.0,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.provider_fallback_used is True
    assert response.provider_fallback_from == "gemini_v1"
    assert response.citations[0].quote.endswith("...")
    assert len(response.citations[0].quote) <= 220


def test_shape_grounded_response_marks_partial_support_without_full_degradation() -> None:
    """Moderate support should stay grounded but be labeled partial for trust UI."""

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="The policy retains employee records for seven years after closure.",
        score=0.02,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="The policy retains employee records for seven years after closure. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": "The policy retains employee records for seven years after closure."},
        generator_provider="local-grounded-v1",
        support_coverage=0.6,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.verification_status == "degraded"
    assert response.support_summary == "partial"
    assert response.degraded_reasons == ["PARTIAL_EVIDENCE"]
    assert response.confidence_label in {"low", "medium"}


def test_shape_grounded_response_marks_ambiguous_support_for_multi_citation_answer() -> None:
    """Moderate multi-citation support should be surfaced as ambiguous rather than fully grounded."""

    first = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="The policy retains employee records for seven years after closure.",
        score=0.03,
    )
    second = _evidence_item(
        citation_id="E002",
        chunk_id="chunk-2",
        text="Access logs are deleted after thirty days unless a legal hold applies.",
        score=0.025,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[first, second],
    )
    draft = GroundedAnswerDraft(
        answer_text=(
            "The policy retains employee records for seven years after closure, while access logs "
            "are deleted after thirty days unless a legal hold applies. [E001] [E002]"
        ),
        cited_evidence_ids=["chunk-1", "chunk-2"],
        citation_snippets={
            "chunk-1": "The policy retains employee records for seven years after closure.",
            "chunk-2": "Access logs are deleted after thirty days unless a legal hold applies.",
        },
        generator_provider="local-grounded-v1",
        support_coverage=0.72,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.verification_status == "degraded"
    assert response.support_summary == "partial"
    assert response.degraded_reasons == ["AMBIGUOUS_SUPPORT"]


@pytest.mark.parametrize(
    "support_coverage,source_diversity,expected_reason",
    [
        (0.6, 1, "PARTIAL_EVIDENCE"),
        (0.72, 2, "AMBIGUOUS_SUPPORT"),
    ],
)
def test_verification_status_consistent_with_degraded_reasons(
    support_coverage: float, source_diversity: int, expected_reason: str
) -> None:
    """A non-empty ``degraded_reasons`` list must imply
    ``verification_status == "degraded"``. Without this invariant,
    downstream UIs cannot tell a passed response from a degraded one
    purely from the reasons list, and the two fields contradict.
    """

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="The policy retains employee records for seven years after closure.",
        score=0.02 if source_diversity == 1 else 0.03,
    )
    cited = [item]
    snippet_map = {
        "chunk-1": "The policy retains employee records for seven years after closure."
    }
    answer = (
        "The policy retains employee records for seven years after closure. [E001]"
    )
    if source_diversity >= 2:
        second = _evidence_item(
            citation_id="E002",
            chunk_id="chunk-2",
            text="Access logs are deleted after thirty days unless a legal hold applies.",
            score=0.025,
        )
        cited.append(second)
        snippet_map["chunk-2"] = (
            "Access logs are deleted after thirty days unless a legal hold applies."
        )
        answer = (
            "The policy retains employee records for seven years after closure, while "
            "access logs are deleted after thirty days unless a legal hold applies. "
            "[E001] [E002]"
        )

    package = EvidencePackage(
        retrieved_chunk_ids=[i.chunk_id for i in cited],
        selected_evidence_ids=[i.chunk_id for i in cited],
        items=cited,
    )
    draft = GroundedAnswerDraft(
        answer_text=answer,
        cited_evidence_ids=[i.chunk_id for i in cited],
        citation_snippets=snippet_map,
        generator_provider="local-grounded-v1",
        support_coverage=support_coverage,
        source_diversity=source_diversity,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.degraded_reasons == [expected_reason]
    assert response.verification_status == "degraded", (
        "verification_status must be 'degraded' whenever degraded_reasons is non-empty"
    )


def test_shape_grounded_response_marks_quote_source_provider_when_snippet_present() -> None:
    """When the provider supplied a snippet, ``quote_source`` stays
    ``"provider"`` (the default) and the quote matches the snippet.
    """

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="The full chunk text spans many sentences and is too long to quote verbatim.",
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="The snippet says: 'short summary'. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": "short summary"},
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.citations[0].quote_source == "provider"
    assert response.citations[0].quote == "short summary"


def test_shape_grounded_response_marks_quote_source_fallback_when_snippet_missing() -> None:
    """When the provider sent no snippet, the response shaping silently
    fell back to the raw chunk text and set ``quote_source`` to
    ``"fallback"`` so UIs can show the citation as lower-trust.
    """

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Raw chunk text used because no snippet was provided.",
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded returns cited answers. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={},  # no snippet at all
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.citations[0].quote_source == "fallback"
    assert response.citations[0].quote == item.text.strip()


def test_shape_grounded_response_marks_quote_source_fallback_when_snippet_empty_string() -> None:
    """An empty-string snippet must also be treated as missing — the
    previous implementation would use ``"" or item.text`` and end up
    with the falsy side, which the new branching handles explicitly.
    """

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Raw chunk text used because the snippet was empty.",
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded returns cited answers. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": "   "},  # whitespace-only
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.citations[0].quote_source == "fallback"
    assert response.citations[0].quote == item.text.strip()


def test_calculate_confidence_diversity_bonus_uses_095_threshold() -> None:
    """The +0.05 high-diversity bonus must apply when diversity_signal is at
    least 0.95 (not only when it is exactly 1.0). For an integer
    ``source_diversity`` the practical range is 0.0 / 0.5 / 1.0, so the
    0.95 threshold is effectively the same as 1.0 today, but pinning the
    explicit threshold prevents future regressions if a non-integer
    ``source_diversity`` is ever supported.

    Regression for the diversity-threshold bug: the old condition
    ``diversity_signal >= 1.0`` was so strict it left no headroom for any
    non-integer diversity in the (0.5, 1.0) range to qualify.
    """

    cited_items = [
        _evidence_item(
            citation_id="E001",
            chunk_id="chunk-1",
            text="Grounded supports tenant-safe uploads.",
            score=0.95,
        ),
        _evidence_item(
            citation_id="E002",
            chunk_id="chunk-2",
            text="It also tracks ingestion job status.",
            score=0.95,
        ),
    ]
    draft_high_diversity = _draft(
        answer_text="Grounded supports tenant-safe uploads. [E001] It also tracks ingestion job status. [E002]",
        support_coverage=0.95,
        source_diversity=2,
    )
    draft_low_diversity = _draft(
        answer_text="Grounded supports tenant-safe uploads. [E001] It also tracks ingestion job status. [E002]",
        support_coverage=0.95,
        source_diversity=1,
    )

    high = _calculate_confidence(cited_items=cited_items, draft=draft_high_diversity)
    low = _calculate_confidence(cited_items=cited_items, draft=draft_low_diversity)

    # High-diversity case must include the +0.05 bonus; low-diversity must not.
    # The gap is the 0.15*(1.0-0.5) weight difference (0.075) plus the bonus (0.05).
    assert high - low == pytest.approx(0.125, abs=1e-4), (
        "expected +0.05 diversity bonus plus the 0.15*(1.0-0.5) component "
        "to widen the gap by ~0.125 between source_diversity=2 and =1"
    )
    assert high >= 0.95, "high-diversity confidence should reach the bonus band"
    assert low < 0.95, "low-diversity confidence must stay below the bonus band"


def _draft(*, answer_text: str, support_coverage: float, source_diversity: int) -> GroundedAnswerDraft:
    return GroundedAnswerDraft(
        answer_text=answer_text,
        cited_evidence_ids=["chunk-1", "chunk-2"],
        citation_snippets={
            "chunk-1": "Grounded supports tenant-safe uploads.",
            "chunk-2": "It also tracks ingestion job status.",
        },
        generator_provider="local-grounded-v1",
        support_coverage=support_coverage,
        source_diversity=source_diversity,
    )
