"""Grounded generation helpers built on top of packaged evidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.gemini_generator import GeminiGenerationError, generate_gemini_draft
from app.core.llm_client import generate_grounded_draft
from app.core.openai_generator import (
    OpenAICompatibleGenerationError,
    generate_openai_compatible_draft,
)
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft


@dataclass(frozen=True)
class GenerationBackend:
    """One concrete grounded generation backend."""

    provider_name: str
    implementation: str = "local"

    def generate(
        self,
        *,
        query_text: str,
        evidence_package: EvidencePackage,
    ) -> GroundedAnswerDraft:
        if self.implementation == "gemini":
            return generate_gemini_draft(
                query_text=query_text,
                evidence_package=evidence_package,
            )
        if self.implementation == "openai_compatible":
            return generate_openai_compatible_draft(
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


def generate_answer_from_evidence(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a grounded answer draft using the current generation backend."""

    backend = resolve_generation_backend()
    try:
        return backend.generate(
            query_text=query_text,
            evidence_package=evidence_package,
        )
    except (GeminiGenerationError, OpenAICompatibleGenerationError):
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
