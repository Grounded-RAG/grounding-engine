"""Authentication routes."""

from urllib.parse import urlencode

import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.config import get_settings
from app.core.database import get_db_session
from app.schemas.auth import (
    AuthSmokeResponse,
    EmailAuthResponse,
    EmailSignInRequest,
    EmailSignUpRequest,
    GoogleOAuthCodeRequest,
    GoogleOAuthStartResponse,
    SSOInitiateRequest,
    SSOInitiateResponse,
)
from app.services.auth import (
    EmailSignInServiceError,
    sign_in_with_google,
    sign_in_with_email_password,
    sign_up_with_email_password,
)

router = APIRouter()


@router.post("/auth/email/sign-up", response_model=EmailAuthResponse)
async def email_sign_up(
    sign_up_request: EmailSignUpRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EmailAuthResponse:
    """Create a preview account using email and password."""

    try:
        (
            tenant,
            workspace,
            api_key_record,
            raw_api_key,
            created_tenant,
            created_workspace,
        ) = await sign_up_with_email_password(
            session=session,
            sign_up_request=sign_up_request,
            api_key_salt=get_settings().api_key_salt,
        )
    except EmailSignInServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return EmailAuthResponse(
        status="authenticated",
        tenant_id=tenant.tenant_id,
        tenant_name=tenant.name,
        subscription_plan=tenant.subscription_plan,
        max_execution_tier=tenant.max_execution_tier,
        api_key_id=api_key_record.key_id,
        api_key_label=api_key_record.label,
        api_key=raw_api_key,
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        workspace_slug=workspace.slug,
        created_tenant=created_tenant,
        created_workspace=created_workspace,
    )


@router.post("/auth/email/sign-in", response_model=EmailAuthResponse)
async def email_sign_in(
    sign_in_request: EmailSignInRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EmailAuthResponse:
    """Sign in to a preview account using email and password."""

    try:
        (
            tenant,
            workspace,
            api_key_record,
            raw_api_key,
            created_tenant,
            created_workspace,
        ) = await sign_in_with_email_password(
            session=session,
            sign_in_request=sign_in_request,
            api_key_salt=get_settings().api_key_salt,
        )
    except EmailSignInServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return EmailAuthResponse(
        status="authenticated",
        tenant_id=tenant.tenant_id,
        tenant_name=tenant.name,
        subscription_plan=tenant.subscription_plan,
        max_execution_tier=tenant.max_execution_tier,
        api_key_id=api_key_record.key_id,
        api_key_label=api_key_record.label,
        api_key=raw_api_key,
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        workspace_slug=workspace.slug,
        created_tenant=created_tenant,
        created_workspace=created_workspace,
    )


@router.get("/auth/google/start", response_model=GoogleOAuthStartResponse)
async def google_oauth_start(redirect_uri: str) -> GoogleOAuthStartResponse:
    """Return the Google OAuth authorization URL for the browser redirect flow."""

    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on this server.",
        )

    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return GoogleOAuthStartResponse(
        authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    )


@router.post("/auth/google/callback", response_model=EmailAuthResponse)
async def google_oauth_callback(
    google_request: GoogleOAuthCodeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EmailAuthResponse:
    """Exchange one Google OAuth authorization code and sign the user in."""

    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not fully configured on this server.",
        )

    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": google_request.code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": google_request.redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=15.0,
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            userinfo_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {token_payload.get('access_token', '')}"},
                timeout=15.0,
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=401, detail=f"Google OAuth exchange failed: {exc}") from exc

    google_email = str(userinfo.get("email") or "").strip().lower()
    if not google_email:
        raise HTTPException(
            status_code=400,
            detail="Google user profile did not contain an email address.",
        )

    try:
        (
            tenant,
            workspace,
            api_key_record,
            raw_api_key,
            created_tenant,
            created_workspace,
        ) = await sign_in_with_google(
            session=session,
            email=google_email,
            full_name=str(userinfo.get("name") or "").strip() or None,
            api_key_salt=settings.api_key_salt,
        )
    except EmailSignInServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return EmailAuthResponse(
        status="authenticated",
        tenant_id=tenant.tenant_id,
        tenant_name=tenant.name,
        subscription_plan=tenant.subscription_plan,
        max_execution_tier=tenant.max_execution_tier,
        api_key_id=api_key_record.key_id,
        api_key_label=api_key_record.label,
        api_key=raw_api_key,
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        workspace_slug=workspace.slug,
        created_tenant=created_tenant,
        created_workspace=created_workspace,
    )


@router.post("/auth/sso/initiate", response_model=SSOInitiateResponse)
async def sso_initiate(
    sso_request: SSOInitiateRequest,
) -> SSOInitiateResponse:
    """Return the SSO/SAML redirect URL for an organization (stub)."""

    return SSOInitiateResponse(
        redirect_url=None,
        message=(
            f"SSO is not yet configured for '{sso_request.organization_slug}'. "
            "Contact your administrator to enable SAML/SSO."
        ),
    )


@router.get("/auth/smoke", response_model=AuthSmokeResponse)
async def auth_smoke(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> AuthSmokeResponse:
    """Return a small authenticated response proving tenant resolution."""

    return AuthSmokeResponse(
        status="authenticated",
        tenant_id=tenant_context.tenant_id,
        tenant_name=tenant_context.tenant_name,
        subscription_plan=tenant_context.subscription_plan,
        max_execution_tier=tenant_context.max_execution_tier,
        api_key_id=tenant_context.api_key_id,
        api_key_label=tenant_context.api_key_label,
    )
