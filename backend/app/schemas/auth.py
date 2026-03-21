"""Authentication response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ExecutionTier, SubscriptionPlan


class AuthSmokeResponse(BaseModel):
    """Authenticated smoke response showing resolved tenant context."""

    status: str
    tenant_id: UUID
    tenant_name: str
    subscription_plan: SubscriptionPlan
    max_execution_tier: ExecutionTier
    api_key_id: UUID
    api_key_label: str
