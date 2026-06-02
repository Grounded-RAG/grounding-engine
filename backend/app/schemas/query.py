"""Structured query response schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExecutionTier


class CitationResponse(BaseModel):
    """Verbatim citation returned alongside a grounded answer."""

    citation_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: UUID
    chunk_index: int = Field(ge=0)
    quote: str = Field(min_length=1)
    quote_source: Literal["provider", "fallback", "snippet"] = "provider"


class QueryRequest(BaseModel):
    """Structured request contract for Standard grounded queries."""

    namespace_id: UUID
    query: str = Field(min_length=1)
    requested_tier: ExecutionTier | None = None
    prefer_async: bool = False


class GroundedAnswerResponse(BaseModel):
    """Structured answer contract for grounded query responses."""

    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(min_length=1)
    citations: list[CitationResponse]
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: Literal["low", "medium", "high"] = "low"
    support_summary: Literal["grounded", "partial", "insufficient"] = "insufficient"
    verification_status: Literal["passed", "degraded"]
    degraded_reasons: list[str] = Field(default_factory=list)
    generator_provider: str = Field(min_length=1, default="degraded-handler-v1")
    provider_backend: str = Field(min_length=1, default="degraded_handler_v1")
    provider_model: str | None = None
    provider_fallback_used: bool = False
    provider_fallback_from: str | None = None
