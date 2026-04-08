"""Grounded generation helpers built on top of packaged evidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.gemini_generator import GeminiGenerationError, generate_gemini_draft
from app.core.llm_client import GroundedGenerationError, generate_grounded_draft
from app.core.openai_generator import (
    OpenAICompatibleGenerationError,
    generate_openai_compatible_draft,
)
from app.core.query_analysis import (
    build_query_profile,
    has_strong_intent_signal,
    is_action_query,
    is_collection_query,
    is_comparison_query,
    is_dataset_summary_query,
    is_definition_query,
    is_entity_context_query,
    is_field_extraction_query,
    is_count_query,
    score_text_against_query,
    tokenize_meaningful_terms,
)
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft
from app.core.telemetry import get_logger


logger = get_logger("app.generation")

_SUMMARY_ANSWER_NOISE = {
    "about",
    "attached",
    "contain",
    "contains",
    "cover",
    "covers",
    "data",
    "dataset",
    "datasets",
    "document",
    "documents",
    "file",
    "files",
    "include",
    "includes",
    "information",
    "item",
    "items",
    "section",
    "sections",
    "summary",
}

_FIELD_ANSWER_NOISE = {
    "answer",
    "contact",
    "details",
    "field",
    "information",
    "is",
    "listed",
    "name",
    "person",
    "the",
}


@dataclass(frozen=True)
class GenerationBackend:
    """One concrete grounded generation backend."""

    provider_name: str
    implementation: str = "local"

    async def generate(
        self,
        *,
        query_text: str,
        evidence_package: EvidencePackage,
    ) -> GroundedAnswerDraft:
        if self.implementation == "gemini":
            return await generate_gemini_draft(
                query_text=query_text,
                evidence_package=evidence_package,
            )
        if self.implementation == "openai_compatible":
            return await generate_openai_compatible_draft(
                query_text=query_text,
                evidence_package=evidence_package,
            )
        return generate_grounded_draft(
            query_text=query_text,
            evidence_package=evidence_package,
        )


_GENERATION_BACKENDS = {
    "local_grounded_v1": GenerationBackend(
        provider_name="local_grounded_v1",
        implementation="local",
    ),
    "gemini_v1": GenerationBackend(
        provider_name="gemini_v1",
        implementation="gemini",
    ),
    "openai_compatible_v1": GenerationBackend(
        provider_name="openai_compatible_v1",
        implementation="openai_compatible",
    ),
}


def resolve_generation_backend() -> GenerationBackend:
    """Return the configured grounded generation backend."""

    backend_name = get_settings().generator_backend
    try:
        return _GENERATION_BACKENDS[backend_name]
    except KeyError as exc:
        raise RuntimeError(
            f"Unsupported generator backend configured: {backend_name}."
        ) from exc


def _provider_draft_is_query_aligned(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
    draft: GroundedAnswerDraft,
) -> bool:
    """Validate provider-generated drafts before they reach the user."""

    profile = build_query_profile(query_text)
    cited_items = [
        item for item in evidence_package.items if item.chunk_id in set(draft.cited_evidence_ids)
    ]
    if not cited_items:
        return False

    if is_dataset_summary_query(profile):
        return _provider_summary_is_query_aligned(
            evidence_package=evidence_package,
            cited_items=cited_items,
            draft=draft,
        )

    if is_action_query(profile):
        return _provider_action_is_query_aligned(
            query_text=query_text,
            cited_items=cited_items,
            draft=draft,
        )

    if is_comparison_query(profile) or is_entity_context_query(profile):
        return _provider_boolean_like_is_query_aligned(
            query_text=query_text,
            cited_items=cited_items,
            draft=draft,
        )

    if is_count_query(profile):
        return _provider_count_is_query_aligned(
            query_text=query_text,
            cited_items=cited_items,
            draft=draft,
        )

    if (
        is_field_extraction_query(profile)
        and not is_collection_query(profile)
        and len(cited_items) > 1
    ):
        return False

    aligned_count = 0
    for item in cited_items:
        snippet = draft.citation_snippets.get(item.chunk_id, item.text)
        if (
            has_strong_intent_signal(snippet, profile=profile)
            or has_strong_intent_signal(item.text, profile=profile)
            or score_text_against_query(
                snippet,
                profile=profile,
                chunk_index=item.chunk_index,
            )
            >= 8.0
        ):
            aligned_count += 1

    if is_field_extraction_query(profile) and not is_collection_query(profile):
        if aligned_count != len(cited_items):
            return False
        return not _field_answer_has_unsupported_terms(
            query_text=query_text,
            cited_items=cited_items,
            draft=draft,
        )

    if is_definition_query(profile):
        return aligned_count >= 1

    return aligned_count >= 1


def _significant_terms(text: str, *, noise_terms: set[str]) -> set[str]:
    return {
        term
        for term in tokenize_meaningful_terms(text)
        if term not in noise_terms
    }


def _provider_summary_is_query_aligned(
    *,
    evidence_package: EvidencePackage,
    cited_items: list,
    draft: GroundedAnswerDraft,
) -> bool:
    """Require provider summaries to cover more than one shallow fragment."""

    answer_terms = _significant_terms(
        draft.answer_text,
        noise_terms=_SUMMARY_ANSWER_NOISE,
    )
    if len(draft.answer_text.split()) < 8 or len(answer_terms) < 2:
        return False

    if len(evidence_package.items) > 1 and len(cited_items) < 2:
        return False

    evidence_terms: set[str] = set()
    for item in cited_items:
        evidence_terms.update(
            _significant_terms(item.text, noise_terms=_SUMMARY_ANSWER_NOISE)
        )

    return len(answer_terms & evidence_terms) >= 2


def _field_answer_has_unsupported_terms(
    *,
    query_text: str,
    cited_items: list,
    draft: GroundedAnswerDraft,
) -> bool:
    """Reject provider field answers that add extra unsupported content."""

    profile = build_query_profile(query_text)
    answer_terms = _significant_terms(
        draft.answer_text,
        noise_terms=_FIELD_ANSWER_NOISE,
    )
    allowed_terms = set()
    for item in cited_items:
        allowed_terms.update(_significant_terms(item.text, noise_terms=set()))
    if profile.attribute_terms:
        for attribute in profile.attribute_terms:
            allowed_terms.update(tokenize_meaningful_terms(attribute))
    allowed_terms.update(profile.semantic_tags)

    unsupported_terms = {
        term for term in answer_terms if term not in allowed_terms
    }
    return len(unsupported_terms) > 1


def _provider_action_is_query_aligned(
    *,
    query_text: str,
    cited_items: list,
    draft: GroundedAnswerDraft,
) -> bool:
    profile = build_query_profile(query_text)
    if len(draft.answer_text.split()) < 8:
        return False
    if not any(
        has_strong_intent_signal(
            draft.citation_snippets.get(item.chunk_id, item.text),
            profile=profile,
        )
        or has_strong_intent_signal(item.text, profile=profile)
        for item in cited_items
    ):
        return False
    return not _field_answer_has_unsupported_terms(
        query_text=query_text,
        cited_items=cited_items,
        draft=draft,
    )


def _provider_boolean_like_is_query_aligned(
    *,
    query_text: str,
    cited_items: list,
    draft: GroundedAnswerDraft,
) -> bool:
    profile = build_query_profile(query_text)
    normalized_answer = draft.answer_text.casefold().strip()
    if not normalized_answer.startswith(("yes", "no")):
        return False
    return any(
        score_text_against_query(
            draft.citation_snippets.get(item.chunk_id, item.text),
            profile=profile,
            chunk_index=item.chunk_index,
        )
        >= 8.0
        for item in cited_items
    )


def _provider_count_is_query_aligned(
    *,
    query_text: str,
    cited_items: list,
    draft: GroundedAnswerDraft,
) -> bool:
    profile = build_query_profile(query_text)
    if not any(character.isdigit() for character in draft.answer_text):
        return False
    return any(
        has_strong_intent_signal(item.text, profile=profile)
        or score_text_against_query(
            item.text,
            profile=profile,
            chunk_index=item.chunk_index,
        )
        >= 8.0
        for item in cited_items
    )


async def generate_answer_from_evidence(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a grounded answer draft using the current generation backend."""

    backend = resolve_generation_backend()
    try:
        draft = await backend.generate(
            query_text=query_text,
            evidence_package=evidence_package,
        )
        if backend.implementation != "local" and not _provider_draft_is_query_aligned(
            query_text=query_text,
            evidence_package=evidence_package,
            draft=draft,
        ):
            raise GroundedGenerationError(
                "Provider generation returned weakly aligned support."
            )
        return draft
    except GroundedGenerationError:
        if backend.implementation == "local":
            raise
        logger.warning(
            "generation_provider_fallback",
            configured_backend=backend.provider_name,
            fallback_backend="local_grounded_v1",
        )
    except (GeminiGenerationError, OpenAICompatibleGenerationError):
        logger.warning(
            "generation_provider_fallback",
            configured_backend=backend.provider_name,
            fallback_backend="local_grounded_v1",
        )
    fallback_draft = generate_grounded_draft(
        query_text=query_text,
        evidence_package=evidence_package,
    )
    return GroundedAnswerDraft(
        answer_text=fallback_draft.answer_text,
        cited_evidence_ids=fallback_draft.cited_evidence_ids,
        citation_snippets=fallback_draft.citation_snippets,
        generator_provider=f"{fallback_draft.generator_provider}:fallback_from_{backend.provider_name}",
        support_coverage=fallback_draft.support_coverage,
        source_diversity=fallback_draft.source_diversity,
    )
