"""Grounded generation helpers built on top of packaged evidence."""

from __future__ import annotations

from app.core.llm_client import generate_grounded_draft
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft


def generate_answer_from_evidence(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a grounded answer draft using the current generation backend."""

    return generate_grounded_draft(
        query_text=query_text,
        evidence_package=evidence_package,
    )
