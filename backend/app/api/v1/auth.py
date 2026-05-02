"""Authentication routes."""

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
)
from app.services.auth import (
    EmailSignInServiceError,
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
