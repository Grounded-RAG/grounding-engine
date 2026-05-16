"""End-to-end answer orchestration for grounded and degraded responses."""

from __future__ import annotations

from app.core.llm_client import GroundedGenerationError
from app.core.telemetry import get_logger
from app.pipeline.contracts import EvidencePackage
from app.schemas.query import GroundedAnswerResponse
from app.services.generation import generate_answer_from_evidence
from app.services.response_shaping import (
    ResponseShapingError,
    shape_degraded_response,
    shape_grounded_response,
)


logger = get_logger("app.answering")


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
    except (GroundedGenerationError, ResponseShapingError) as exc:
        logger.warning(
            "answer_from_evidence_failed",
            reason=str(exc),
            evidence_count=len(evidence_package.items),
        )
        if "configured generation provider" in str(exc).lower():
            return shape_degraded_response(
                reason="GENERATION_PROVIDER_FAILED",
                answer_text=(
                    "I do not have an answer for this request because the configured "
                    "model could not produce a grounded response."
                ),
            )
        return shape_degraded_response(
            reason="INSUFFICIENT_SUPPORT",
            answer_text=(
                "I found some related material, but not enough grounded evidence "
                "to answer confidently."
            ),
        )
