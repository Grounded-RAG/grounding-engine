"""Shared API dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.database import get_db_session
from app.core.security import hash_api_key
from app.core.telemetry import bind_tenant_context
from app.models import APIKey, ExecutionTier, SubscriptionPlan


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    """Authenticated tenant context derived from an API key."""

    tenant_id: UUID
    tenant_name: str
    subscription_plan: SubscriptionPlan
    max_execution_tier: ExecutionTier
    api_key_id: UUID
    api_key_label: str


def _unauthorized(detail: str) -> HTTPException:
    """Create a consistent unauthorized error response."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def get_raw_api_key(
    x_api_key: str | None = Depends(api_key_header),
    bearer_credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Extract the API key from supported request headers."""

    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if (
        bearer_credentials is not None
        and bearer_credentials.scheme.lower() == "bearer"
        and bearer_credentials.credentials.strip()
    ):
        return bearer_credentials.credentials.strip()
    raise _unauthorized("API key is required.")


async def get_tenant_context(
    request: Request,
    raw_api_key: str = Depends(get_raw_api_key),
    session: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    """Resolve a tenant context from an API key."""

    settings = get_settings()
    api_key_hash = hash_api_key(raw_api_key, settings.api_key_salt)
    statement = (
        select(APIKey)
        .options(selectinload(APIKey.tenant))
        .where(APIKey.key_hash == api_key_hash)
    )
    result = await session.execute(statement)
    api_key_record = result.scalar_one_or_none()

    if api_key_record is None:
        raise _unauthorized("API key is invalid.")
    if api_key_record.revoked_at is not None:
        raise _unauthorized("API key has been revoked.")
    if api_key_record.tenant is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key tenant binding is invalid.",
        )

    bind_tenant_context(
        tenant_id=str(api_key_record.tenant.tenant_id),
        api_key_id=str(api_key_record.key_id),
    )
    request.state.tenant_id = str(api_key_record.tenant.tenant_id)

    return TenantContext(
        tenant_id=api_key_record.tenant.tenant_id,
        tenant_name=api_key_record.tenant.name,
        subscription_plan=api_key_record.tenant.subscription_plan,
        max_execution_tier=api_key_record.tenant.max_execution_tier,
        api_key_id=api_key_record.key_id,
        api_key_label=api_key_record.label,
    )
