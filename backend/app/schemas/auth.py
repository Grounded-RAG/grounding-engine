"""Authentication response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.models.enums import PlanTier


class AuthSmokeResponse(BaseModel):
    """Authenticated smoke response showing resolved tenant context."""

    status: str
    tenant_id: UUID
    tenant_name: str
    plan_tier: PlanTier
    api_key_id: UUID
    api_key_label: str
