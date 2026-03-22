"""Structured query response schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CitationResponse(BaseModel):
    """Verbatim citation returned alongside a grounded answer."""

    citation_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: UUID
    chunk_index: int = Field(ge=0)
    quote: str = Field(min_length=1)


class GroundedAnswerResponse(BaseModel):
    """Structured answer contract for grounded query responses."""

    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(min_length=1)
    citations: list[CitationResponse]
    confidence_score: float = Field(ge=0.0, le=1.0)
    verification_status: Literal["passed", "degraded"]
