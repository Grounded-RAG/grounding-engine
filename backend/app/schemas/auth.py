"""Authentication request and response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ExecutionTier, SubscriptionPlan


class EmailSignInRequest(BaseModel):
    """Preview email sign-in request used by the frontend login page."""

    email: str = Field(min_length=3, max_length=320)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_name: str | None = Field(default=None, min_length=1, max_length=255)
    workspace_name: str | None = Field(default=None, min_length=1, max_length=255)


class AuthSmokeResponse(BaseModel):
    """Authenticated smoke response showing resolved tenant context."""

    status: str
    tenant_id: UUID
    tenant_name: str
    subscription_plan: SubscriptionPlan
    max_execution_tier: ExecutionTier
    api_key_id: UUID
    api_key_label: str


class EmailSignInResponse(AuthSmokeResponse):
    """Response returned after preview email sign-in succeeds."""

    api_key: str
    workspace_id: UUID
    workspace_name: str
    created_tenant: bool = False
    created_workspace: bool = False
