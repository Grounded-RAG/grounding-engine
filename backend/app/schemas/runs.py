"""Run history API schemas backed by persisted query traces."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ExecutionTier, UserFacingMode
from app.schemas.query import CitationResponse

FEEDBACK_REASONS = Literal[
    "FAILS_TO_ANSWER",
    "HALLUCINATION",
    "IRRELEVANT_INFORMATION",
    "WRONG_CITATIONS",
    "PROSE_ERRORS",
    "OTHER",
]


class FeedbackSubmission(BaseModel):
    rating: Literal["positive", "negative"]
    reasons: list[FEEDBACK_REASONS] = Field(default_factory=list)
    freeform_text: str | None = Field(default=None, max_length=4000)


class RunResponse(BaseModel):
    """Product-facing run record backed by one persisted query trace."""

    run_id: UUID
    status: Literal["queued", "running", "completed", "failed"] = "completed"
    dataset_id: UUID | None
    agent_id: UUID | None = None
    conversation_id: UUID | None = None
    selected_mode: UserFacingMode | None = None
    requested_tier: ExecutionTier | None
    router_recommendation: ExecutionTier
    effective_tier: ExecutionTier
    routing_reason: str = Field(min_length=1)
    query: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    citations: list[CitationResponse]
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: Literal["low", "medium", "high"]
    support_summary: Literal["grounded", "partial", "insufficient"]
    verification_status: Literal["passed", "degraded"]
    degraded_reasons: list[str]
    generator_provider: str = Field(min_length=1)
    provider_backend: str = Field(min_length=1)
    provider_model: str | None = None
    provider_fallback_used: bool = False
    provider_fallback_from: str | None = None
    retrieved_chunk_ids: list[str]
    selected_evidence_ids: list[str]
    stage_latencies_ms: dict[str, int] = Field(default_factory=dict)
    total_latency_ms: int = Field(ge=0)
    feedback_rating: Literal["positive", "negative"] | None = None
    feedback_reasons: list[str] = Field(default_factory=list)
    feedback_text: str | None = None
    created_at: datetime
