"""API key management schemas for the product shell."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreateRequest(BaseModel):
    """Request used to issue one new API key for the authenticated tenant."""

    label: str = Field(min_length=1, max_length=255)


class APIKeyResponse(BaseModel):
    """Tenant-scoped API key metadata safe to return after creation or listing."""

    model_config = ConfigDict(from_attributes=True)

    key_id: UUID
    label: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class APIKeyCreateResponse(APIKeyResponse):
    """API key creation response that returns the raw key value exactly once."""

    api_key: str = Field(min_length=1)
