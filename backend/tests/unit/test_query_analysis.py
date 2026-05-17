"""Unit tests for generic query analysis helpers."""

from __future__ import annotations

from app.core.query_analysis import (
    build_conversation_context,
    build_query_plan,
    build_query_profile,
    final_answer_mode,
    is_action_query,
    is_collection_query,
    is_comparison_query,
    is_count_query,
    is_definition_query,
    is_entity_context_query,
    primary_intent,
    query_plan_metadata,
    refine_query_plan_for_execution_tier,
    requested_attribute_label,
)
from app.models import ExecutionTier


def test_build_query_profile_detects_dataset_summary_with_common_typo() -> None:
    """Dataset-summary detection should tolerate light misspellings in the query."""

    profile = build_query_profile("what isthe datatset about")

    assert profile.query_kind == "summary"


def test_build_query_profile_extracts_generic_attribute_phrase() -> None:
    """Attribute extraction should work for general domain questions, not just resumes."""

    profile = build_query_profile("What is the pricing model of this service?")

    assert "pricing model" in profile.attribute_terms
    assert profile.query_kind == "lookup"


def test_build_query_profile_routes_concept_what_is_question_as_definition() -> None:
    """Concept explanations should not be handled as exact field extraction."""

    profile = build_query_profile("What is continual learning? How does it work?")

    assert profile.query_kind == "definition"
    assert is_definition_query(profile) is True
    assert final_answer_mode(profile) == "open"


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


def test_build_query_profile_splits_multi_collection_attributes_cleanly() -> None:
    """Collection questions with multiple requested item families should preserve both concepts."""

    profile = build_query_profile("What are the methods, the tools?")

    assert profile.query_kind == "list"
    assert "method" in profile.attribute_terms
    assert "tool" in profile.attribute_terms
    assert requested_attribute_label(profile) == "methods and tools"


def test_build_query_profile_detects_company_lookup_query() -> None:
    """Supplier/company questions should route as focused lookups, not open chat."""

    profile = build_query_profile("Which company supplied the vans?")

    assert profile.query_kind == "lookup"
    assert "company" in profile.attribute_terms
    assert requested_attribute_label(profile) == "company"


def test_build_query_profile_detects_difference_question_as_comparison() -> None:
    """Difference questions should route to comparison handling rather than generic lookup."""

    profile = build_query_profile(
        "What was the difference between old fuel cost and new electricity cost over six months?"
    )

    assert profile.query_kind == "comparison"


def test_final_answer_mode_routes_event_lookup_question() -> None:
    """Dated incident questions should route to event lookup mode."""

    profile = build_query_profile("What happened in April 2025?")

    assert final_answer_mode(profile) == "event_lookup"


def test_final_answer_mode_routes_recommendation_question() -> None:
    """Recommendation questions should use list/recommendation mode even when lookup-like."""

    profile = build_query_profile("What did the committee recommend in August 2025?")

    assert final_answer_mode(profile) == "list_or_recommendation"


def test_final_answer_mode_routes_net_savings_question_to_arithmetic() -> None:
    """Savings questions that require computation should use arithmetic mode."""

    profile = build_query_profile("What was the net savings after including installation costs?")

    assert final_answer_mode(profile) == "arithmetic_qa"


def test_build_query_profile_detects_when_start_end_query_as_date_lookup() -> None:
    """When-start-end questions should keep date semantics for exact date-range answers."""

    profile = build_query_profile("When did the pilot start and end?")

    assert profile.query_kind == "lookup"
    assert "date" in profile.semantic_tags


def test_build_query_profile_prefers_universal_contact_semantics() -> None:
    """Universal semantic tags like contact should survive noisy wording."""

    profile = build_query_profile("What is the email address for the customer?")

    assert primary_intent(profile) == "contact"
    assert requested_attribute_label(profile) == "contact"


def test_build_query_plan_creates_retrieval_rewrites_for_lookup_query() -> None:
    """Standard query planning should create a few focused retrieval rewrites."""

    plan = build_query_plan("What is the pricing model of this service?")

    assert plan.profile.query_kind == "lookup"
    assert len(plan.retrieval_queries) == 2
    assert plan.retrieval_queries[0] == "what is the pricing model of this service"
    assert any("pricing model" in query.casefold() for query in plan.retrieval_queries)
    assert "kind=lookup" in plan.explanation


def test_build_query_plan_expands_morphological_aliases_for_retrieval() -> None:
    """Retrieval rewrites should bridge small wording differences like miner vs mining."""

    plan = build_query_plan("Did she work in pattern miner?")

    assert any("mining" in query.casefold() for query in plan.retrieval_queries)


def test_refine_query_plan_for_standard_keeps_standard_variants() -> None:
    """Standard refinement should be a no-op to preserve the baseline behavior."""

    plan = build_query_plan("Compare option A and option B deployment costs.")

    refined = refine_query_plan_for_execution_tier(
        plan,
        execution_tier=ExecutionTier.STANDARD,
    )

    assert refined == plan


def test_refine_query_plan_for_enterprise_adds_controlled_comparison_rewrites() -> None:
    """Enterprise planning should add a few extra retrieval intents for hard comparisons."""

    plan = build_query_plan("Compare option A and option B deployment costs and staffing.")

    refined = refine_query_plan_for_execution_tier(
        plan,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    assert len(refined.retrieval_queries) > len(plan.retrieval_queries)
    assert any("difference" in query.casefold() for query in refined.retrieval_queries)
    assert "enterprise_planning=true" in refined.explanation


def test_refine_query_plan_for_enterprise_adds_follow_up_focus_variant() -> None:
    """Enterprise planning should keep a controlled follow-up variant for context-heavy queries."""

    conversation_context = build_conversation_context(
        recent_user_queries=[
            "What did she do at iCog Labs?",
            "What about the previous document?",
        ],
    )
    assert conversation_context is not None
    plan = build_query_plan(
        "did it mention pattern miner there",
        conversation_context=conversation_context,
    )

    refined = refine_query_plan_for_execution_tier(
        plan,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    assert len(refined.retrieval_queries) >= len(plan.retrieval_queries)
    assert any("follow up" in query.casefold() for query in refined.retrieval_queries)


def test_refine_query_plan_for_enterprise_decomposes_start_end_lookup() -> None:
    """Enterprise planning should decompose start/end lookups into bounded date intents."""

    plan = build_query_plan("When did the pilot start and end?")

    refined = refine_query_plan_for_execution_tier(
        plan,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    assert any("start date" in query.casefold() for query in refined.retrieval_queries)
    assert any("end date" in query.casefold() for query in refined.retrieval_queries)


def test_refine_query_plan_for_enterprise_decomposes_multi_attribute_lookup() -> None:
    """Enterprise planning should split multi-attribute lookups into tighter attribute queries."""

    plan = build_query_plan("What are the methods, the tools?")

    refined = refine_query_plan_for_execution_tier(
        plan,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    assert len(refined.retrieval_queries) > len(plan.retrieval_queries)
    assert any("method" in query.casefold() for query in refined.retrieval_queries)
    assert any("tool" in query.casefold() for query in refined.retrieval_queries)


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


def test_build_query_profile_routes_mixed_boolean_action_question_as_action() -> None:
    """Role + where + what-did follow-ups should route as action queries."""

    profile = build_query_profile(
        "does she has an experiance as a AI enginner if so where and what did she do there"
    )

    assert is_action_query(profile) is True
    assert any("ai eng" in context for context in profile.context_terms)


def test_build_query_profile_treats_whose_question_as_name_lookup() -> None:
    """Owner-style whose phrasing should still resolve to a name lookup."""

    profile = build_query_profile("whose resume is this please")

    assert profile.query_kind == "lookup"
    assert "name" in profile.attribute_terms


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
