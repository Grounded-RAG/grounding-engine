"""Unit tests for generic query analysis helpers."""

from __future__ import annotations

from app.core.query_analysis import (
    build_conversation_context,
    build_query_plan,
    build_query_profile,
    is_action_query,
    is_collection_query,
    is_comparison_query,
    is_count_query,
    is_entity_context_query,
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


def test_build_query_profile_detects_included_features_query_as_collection() -> None:
    """Collection phrasing like 'what features are included' should still route as list queries."""

    profile = build_query_profile("What features are included?")

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


def test_build_query_profile_detects_action_queries_with_context() -> None:
    """Action queries should preserve their context and route as action questions."""

    profile = build_query_profile("What did she do at iCog Labs?")

    assert is_action_query(profile) is True
    assert "icog labs" in profile.context_terms


def test_build_query_profile_detects_comparison_queries() -> None:
    """Comparison-style yes/no questions should not collapse into plain boolean routing."""

    profile = build_query_profile("Is her experience only in iCog or is there some other one?")

    assert is_comparison_query(profile) is True
    assert "experience" in profile.attribute_terms


def test_build_query_profile_detects_entity_in_context_queries() -> None:
    """Entity-in-context questions should preserve the topic phrase they are asking about."""

    profile = build_query_profile("Did she work on pattern miner?")

    assert is_entity_context_query(profile) is True
    assert "pattern miner" in profile.context_terms


def test_build_query_profile_detects_count_queries() -> None:
    """Count questions should be routed separately from generic list questions."""

    profile = build_query_profile("How many projects does she have?")

    assert is_count_query(profile) is True
    assert "projects" in profile.attribute_terms or "project" in profile.attribute_terms


def test_build_query_plan_preserves_document_reference_follow_up_scope() -> None:
    """Document-order follow-ups should inherit summary scope from the prior turn."""

    plan = build_query_plan(
        "what about the second document",
        previous_user_query="What is the dataset about?",
    )

    assert plan.used_conversation_context is True
    assert plan.profile.document_reference_rank == 2
    assert plan.profile.query_kind == "summary"
    assert "document_reference_rank=2" in plan.explanation


def test_build_query_plan_reuses_previous_context_for_reference_follow_up() -> None:
    """Reference-heavy follow-ups should preserve the prior contextual target when needed."""

    plan = build_query_plan(
        "did it mention pattern miner there",
        previous_user_query="What did she do at iCog Labs?",
    )

    assert plan.used_conversation_context is True
    assert "icog labs" in plan.resolved_query_text.casefold()


def test_build_query_plan_uses_long_history_conversation_context() -> None:
    """Follow-ups should be able to recover context from a small rolling history window."""

    conversation_context = build_conversation_context(
        recent_user_queries=[
            "What is her work experience?",
            "What did she do at iCog Labs?",
            "What about the internship?",
        ],
        recent_assistant_messages=[
            "She worked as an AI Engineer at iCog Labs and later as a Backend | AI Developer Intern at iCog Labs.",
        ],
    )

    assert conversation_context is not None
    plan = build_query_plan(
        "did it mention pattern miner there",
        conversation_context=conversation_context,
    )

    assert plan.used_conversation_context is True
    assert "icog labs" in plan.resolved_query_text.casefold()
    assert "pattern miner" in plan.resolved_query_text.casefold()


def test_build_query_plan_preserves_document_reference_from_recent_history() -> None:
    """Reference-only follow-ups should inherit a recent document ordinal when available."""

    conversation_context = build_conversation_context(
        recent_user_queries=[
            "What is the dataset about?",
            "What about the second document?",
        ],
    )

    assert conversation_context is not None
    plan = build_query_plan(
        "did it mention pricing there",
        conversation_context=conversation_context,
    )

    assert plan.used_conversation_context is True
    assert "second document" in plan.resolved_query_text.casefold()


def test_build_query_plan_resolves_relative_document_follow_up_from_recent_history() -> None:
    """Relative document follow-ups should reuse recent document ordering context."""

    conversation_context = build_conversation_context(
        recent_user_queries=[
            "What is the first document about?",
            "What about the second document?",
        ],
    )

    assert conversation_context is not None
    plan = build_query_plan(
        "what about the previous document",
        conversation_context=conversation_context,
    )

    assert plan.used_conversation_context is True
    assert "first document" in plan.resolved_query_text.casefold()
