"""Grounded generation helpers built on top of packaged evidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.llm_client import generate_grounded_draft
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft


@dataclass(frozen=True)
class GenerationBackend:
    """One concrete grounded generation backend."""

    provider_name: str

    def generate(
        self,
        *,
        query_text: str,
        evidence_package: EvidencePackage,
    ) -> GroundedAnswerDraft:
        return generate_grounded_draft(
            query_text=query_text,
            evidence_package=evidence_package,
        )


_GENERATION_BACKENDS = {
    "local_grounded_v1": GenerationBackend(provider_name="local_grounded_v1"),
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

    return resolve_generation_backend().generate(
        query_text=query_text,
        evidence_package=evidence_package,
    )
