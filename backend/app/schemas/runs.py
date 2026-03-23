"""Run history API schemas backed by persisted query traces."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ExecutionTier, UserFacingMode
from app.schemas.query import CitationResponse


class RunResponse(BaseModel):
    """Product-facing run record backed by one persisted query trace."""

    run_id: UUID
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
    verification_status: Literal["passed", "degraded"]
    degraded_reasons: list[str]
    generator_provider: str = Field(min_length=1)
    retrieved_chunk_ids: list[str]
    selected_evidence_ids: list[str]
    total_latency_ms: int = Field(ge=0)
    created_at: datetime
