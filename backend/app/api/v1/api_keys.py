"""API key management routes for the product shell."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.api_keys import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyResponse
from app.services.audit_logs import write_audit_log
from app.services.api_keys import (
    APIKeyServiceError,
    create_api_key,
    list_api_keys_for_tenant,
    revoke_api_key,
)


router = APIRouter()


def _build_api_key_response(api_key) -> APIKeyResponse:
    """Project one persisted API key into the safe product response shape."""

    return APIKeyResponse.model_validate(api_key)


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys_route(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[APIKeyResponse]:
    """List API keys owned by the authenticated tenant."""

    api_keys = await list_api_keys_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
    )
    return [_build_api_key_response(api_key) for api_key in api_keys]


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key_route(
    create_request: APIKeyCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> APIKeyCreateResponse:
    """Issue one new API key for the authenticated tenant."""

    try:
        api_key, raw_api_key = await create_api_key(
            session=session,
            tenant_id=tenant_context.tenant_id,
            create_request=create_request,
        )
    except APIKeyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    await write_audit_log(
        session=session,
        tenant_id=tenant_context.tenant_id,
        actor_key_id=tenant_context.api_key_id,
        action="api_key.created",
        resource_type="api_key",
        resource_id=str(api_key.key_id),
        summary=f"API key '{api_key.label}' created",
    )

    return APIKeyCreateResponse(
        key_id=api_key.key_id,
        label=api_key.label,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        created_at=api_key.created_at,
        api_key=raw_api_key,
    )


@router.post("/api-keys/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key_route(
    key_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> APIKeyResponse:
    """Revoke one tenant-scoped API key."""

    try:
        api_key = await revoke_api_key(
            session=session,
            tenant_id=tenant_context.tenant_id,
            key_id=key_id,
        )
    except APIKeyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    await write_audit_log(
        session=session,
        tenant_id=tenant_context.tenant_id,
        actor_key_id=tenant_context.api_key_id,
        action="api_key.revoked",
        resource_type="api_key",
        resource_id=str(key_id),
        summary=f"API key '{api_key.label}' revoked",
    )

    return _build_api_key_response(api_key)
