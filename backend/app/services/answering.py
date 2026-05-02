"""End-to-end answer orchestration for grounded and degraded responses."""

from __future__ import annotations

from app.core.llm_client import GroundedGenerationError
from app.pipeline.contracts import EvidencePackage
from app.schemas.query import GroundedAnswerResponse
from app.services.generation import generate_answer_from_evidence
from app.services.response_shaping import (
    ResponseShapingError,
    shape_degraded_response,
    shape_grounded_response,
)


async def answer_from_evidence(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerResponse:
    """Return a grounded or degraded response from the available evidence."""

    if not evidence_package.items:
        return shape_degraded_response(
            reason="NO_GROUNDED_EVIDENCE",
            answer_text="I could not find grounded evidence for this query.",
        )

    try:
        draft = await generate_answer_from_evidence(
            query_text=query_text,
            evidence_package=evidence_package,
        )
        return shape_grounded_response(
            draft=draft,
            evidence_package=evidence_package,
        )
    except (GroundedGenerationError, ResponseShapingError):
        return shape_degraded_response(
            reason="INSUFFICIENT_SUPPORT",
            answer_text=(
                "I found some related material, but not enough grounded evidence "
                "to answer confidently."
            ),
        )
