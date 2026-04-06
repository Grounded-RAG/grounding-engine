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
    is_collection_query,
    is_dataset_summary_query,
    is_definition_query,
    is_field_extraction_query,
    score_text_against_query,
)
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft
from app.core.telemetry import get_logger


logger = get_logger("app.generation")


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
        return len(cited_items) >= 1

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
        return aligned_count == len(cited_items)

    if is_definition_query(profile):
        return aligned_count >= 1

    return aligned_count >= 1


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
