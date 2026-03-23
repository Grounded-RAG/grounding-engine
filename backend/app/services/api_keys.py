"""API key management services for the product shell."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import generate_api_key, hash_api_key
from app.models import APIKey
from app.schemas.api_keys import APIKeyCreateRequest


class APIKeyServiceError(RuntimeError):
    """Raised when an API key management operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _normalize_label(label: str) -> str:
    """Normalize an API key label while rejecting blank values."""

    normalized = label.strip()
    if not normalized:
        raise APIKeyServiceError(
            "API key label must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


async def _get_api_key_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
) -> APIKey:
    """Resolve one API key only if it belongs to the authenticated tenant."""

    statement = select(APIKey).where(
        APIKey.tenant_id == tenant_id,
        APIKey.key_id == key_id,
    )
    result = await session.execute(statement)
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise APIKeyServiceError(
            "API key not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return api_key


async def list_api_keys_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[APIKey]:
    """Return API keys owned by one tenant, newest first."""

    statement = (
        select(APIKey)
        .where(APIKey.tenant_id == tenant_id)
        .order_by(APIKey.created_at.desc(), APIKey.key_id.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def create_api_key(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    create_request: APIKeyCreateRequest,
) -> tuple[APIKey, str]:
    """Issue one new API key and return the persisted row plus raw secret once."""

    raw_api_key = generate_api_key()
    api_key = APIKey(
        tenant_id=tenant_id,
        label=_normalize_label(create_request.label),
        key_hash=hash_api_key(raw_api_key, get_settings().api_key_salt),
    )
    session.add(api_key)

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise APIKeyServiceError(
            "Failed to create API key.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(api_key)
    return api_key, raw_api_key


async def revoke_api_key(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
) -> APIKey:
    """Revoke one tenant-scoped API key. This operation is idempotent."""

    api_key = await _get_api_key_for_tenant(
        session=session,
        tenant_id=tenant_id,
        key_id=key_id,
    )

    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(UTC)
        try:
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise APIKeyServiceError(
                "Failed to revoke API key.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        await session.refresh(api_key)

    return api_key
