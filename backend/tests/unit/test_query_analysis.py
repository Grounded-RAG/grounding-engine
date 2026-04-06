"""Unit tests for generic query analysis helpers."""

from __future__ import annotations

from app.core.query_analysis import (
    build_query_plan,
    build_query_profile,
    is_collection_query,
    primary_intent,
    query_plan_metadata,
    requested_attribute_label,
)


def test_build_query_profile_detects_dataset_summary_with_common_typo() -> None:
    """Dataset-summary detection should tolerate light misspellings in the query."""

    profile = build_query_profile("what isthe datatset about")

    assert profile.query_kind == "summary"


def test_build_query_profile_extracts_generic_attribute_phrase() -> None:
    """Attribute extraction should work for general domain questions, not just resumes."""

    profile = build_query_profile("What is the pricing model of this service?")

    assert "pricing model" in profile.attribute_terms
    assert profile.query_kind == "lookup"


def test_build_query_profile_corrects_common_attribute_typo() -> None:
    """Common misspellings in focused attribute questions should still resolve cleanly."""

    profile = build_query_profile("what is her work experiance")

    assert profile.query_kind == "lookup"
    assert "work experience" in profile.attribute_terms


def test_build_query_profile_marks_collection_queries_generically() -> None:
    """Collection-style questions should be recognized from generic attribute wording."""

    profile = build_query_profile("What are the supported languages?")

    assert profile.query_kind == "list"
    assert is_collection_query(profile) is True


def test_build_query_profile_prefers_universal_contact_semantics() -> None:
    """Universal semantic tags like contact should survive noisy wording."""

    profile = build_query_profile("What is the email address for the customer?")

    assert primary_intent(profile) == "contact"
    assert requested_attribute_label(profile) == "contact"


def test_build_query_plan_creates_retrieval_rewrites_for_lookup_query() -> None:
    """Standard query planning should create a few focused retrieval rewrites."""

    plan = build_query_plan("What is the pricing model of this service?")

    assert plan.profile.query_kind == "lookup"
    assert len(plan.retrieval_queries) >= 2
    assert any("pricing model" in query.casefold() for query in plan.retrieval_queries)
    assert "kind=lookup" in plan.explanation


def test_build_query_plan_expands_morphological_aliases_for_retrieval() -> None:
    """Retrieval rewrites should bridge small wording differences like miner vs mining."""

    plan = build_query_plan("Did she work in pattern miner?")

    assert any("mining" in query.casefold() for query in plan.retrieval_queries)


def test_build_query_plan_uses_previous_user_query_for_underspecified_follow_up() -> None:
    """Very underspecified follow-ups may safely borrow context from the prior user turn."""

    plan = build_query_plan(
        "what about that",
        previous_user_query="What are the supported programming languages?",
    )

    assert plan.used_conversation_context is True
    assert "language" in plan.resolved_query_text.casefold()


def test_query_plan_metadata_is_trace_safe() -> None:
    """Query plan metadata should be serializable for trace storage."""

    plan = build_query_plan("What is the dataset about?")

    payload = query_plan_metadata(plan)

    assert payload["query_kind"] == "summary"
    assert isinstance(payload["retrieval_queries"], list)
