"""Authentication request and response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ExecutionTier, SubscriptionPlan


class EmailSignInRequest(BaseModel):
    """Email/password sign-in request."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class EmailSignUpRequest(BaseModel):
    """Email/password sign-up request."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
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


class EmailAuthResponse(AuthSmokeResponse):
    """Response returned after email auth succeeds."""

    api_key: str
    workspace_id: UUID | None = None
    workspace_name: str | None = None
    workspace_slug: str | None = None
    created_tenant: bool = False
    created_workspace: bool = False


class GoogleAuthRequest(BaseModel):
    """Google OAuth sign-in request carrying the ID token from the browser."""

    id_token: str = Field(min_length=1, max_length=4096)


class GoogleOAuthStartResponse(BaseModel):
    """Response returning the Google OAuth authorization URL."""

    authorization_url: str


class GoogleOAuthCodeRequest(BaseModel):
    """Google OAuth callback payload carrying the authorization code."""

    code: str = Field(min_length=1, max_length=4096)
    redirect_uri: str = Field(min_length=1, max_length=2048)


class SSOInitiateRequest(BaseModel):
    """Request to initiate an SSO/SAML flow."""

    organization_slug: str = Field(min_length=1, max_length=120)


class SSOInitiateResponse(BaseModel):
    """Response returning the SSO redirect URL."""

    redirect_url: str | None
    message: str
