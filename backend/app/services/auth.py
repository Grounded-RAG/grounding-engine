"""Preview email sign-in services for local product access."""

from __future__ import annotations

import re
import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key, hash_api_key
from app.models import APIKey, ExecutionTier, SubscriptionPlan, Tenant, Workspace
from app.schemas.auth import EmailSignInRequest
from app.schemas.workspaces import WorkspaceCreateRequest
from app.services.workspaces import create_workspace


class EmailSignInServiceError(RuntimeError):
    """Raised when preview email sign-in cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or not _EMAIL_RE.match(normalized):
        raise EmailSignInServiceError(
            "Enter a valid work email address.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.strip().lower()).strip("-")


def _derive_tenant_name(
    *,
    email: str,
    full_name: str | None,
    organization_name: str | None,
) -> str:
    base = organization_name or full_name or email.split("@", maxsplit=1)[0]
    normalized = base.strip()
    return normalized[:255] or "Grounded Workspace"


def _derive_workspace_name(
    *,
    email: str,
    full_name: str | None,
    organization_name: str | None,
    workspace_name: str | None,
) -> str:
    return (
        workspace_name
        or organization_name
        or (f"{full_name}'s Workspace" if full_name else None)
        or f"{email.split('@', maxsplit=1)[0]} workspace"
    )[:255]


async def _get_tenant_by_owner_email(
    *,
    session: AsyncSession,
    owner_email: str,
) -> Tenant | None:
    statement = select(Tenant).where(
        Tenant.default_policy.op("->>")("owner_email") == owner_email,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _build_unique_tenant_name(
    *,
    session: AsyncSession,
    desired_name: str,
) -> str:
    candidate = desired_name
    suffix = 1
    while True:
        statement = select(Tenant.tenant_id).where(Tenant.name == candidate)
        result = await session.execute(statement)
        if result.scalar_one_or_none() is None:
            return candidate
        suffix += 1
        candidate = f"{desired_name} {suffix}"[:255]


async def _create_tenant_for_email(
    *,
    session: AsyncSession,
    email: str,
    full_name: str | None,
    organization_name: str | None,
) -> Tenant:
    tenant_name = await _build_unique_tenant_name(
        session=session,
        desired_name=_derive_tenant_name(
            email=email,
            full_name=full_name,
            organization_name=organization_name,
        ),
    )

    tenant = Tenant(
        name=tenant_name,
        subscription_plan=SubscriptionPlan.FREE,
        max_execution_tier=ExecutionTier.STANDARD,
        default_policy={
            "tier": ExecutionTier.STANDARD.value,
            "owner_email": email,
            "auth_provider": "email_preview",
        },
        retention_days=365,
    )
    session.add(tenant)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EmailSignInServiceError(
            "Failed to create tenant for email sign-in.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(tenant)
    return tenant


async def _get_or_create_workspace(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
    full_name: str | None,
    organization_name: str | None,
    workspace_name: str | None,
) -> tuple[Workspace, bool]:
    statement = (
        select(Workspace)
        .where(Workspace.tenant_id == tenant_id)
        .order_by(Workspace.created_at.asc(), Workspace.workspace_id.asc())
    )
    result = await session.execute(statement)
    existing_workspace = result.scalar_one_or_none()
    if existing_workspace is not None:
        return existing_workspace, False

    workspace = await create_workspace(
        session=session,
        tenant_id=tenant_id,
        workspace_request=WorkspaceCreateRequest(
            name=_derive_workspace_name(
                email=email,
                full_name=full_name,
                organization_name=organization_name,
                workspace_name=workspace_name,
            ),
            slug=_slugify(
                _derive_workspace_name(
                    email=email,
                    full_name=full_name,
                    organization_name=organization_name,
                    workspace_name=workspace_name,
                ),
            )
            or None,
            description="Provisioned from preview email sign-in.",
        ),
    )
    return workspace, True


async def issue_preview_email_sign_in(
    *,
    session: AsyncSession,
    sign_in_request: EmailSignInRequest,
    api_key_salt: str,
) -> tuple[Tenant, Workspace, APIKey, str, bool, bool]:
    """Find or create a preview tenant/workspace, then issue a fresh API key."""

    email = _normalize_email(sign_in_request.email)
    full_name = _normalize_optional(sign_in_request.full_name)
    organization_name = _normalize_optional(sign_in_request.organization_name)
    workspace_name = _normalize_optional(sign_in_request.workspace_name)

    tenant = await _get_tenant_by_owner_email(session=session, owner_email=email)
    created_tenant = tenant is None
    if tenant is None:
        tenant = await _create_tenant_for_email(
            session=session,
            email=email,
            full_name=full_name,
            organization_name=organization_name,
        )

    workspace, created_workspace = await _get_or_create_workspace(
        session=session,
        tenant_id=tenant.tenant_id,
        email=email,
        full_name=full_name,
        organization_name=organization_name,
        workspace_name=workspace_name,
    )

    raw_api_key = generate_api_key()
    api_key_record = APIKey(
        tenant_id=tenant.tenant_id,
        label=f"email-signin:{email}",
        key_hash=hash_api_key(raw_api_key, api_key_salt),
    )
    session.add(api_key_record)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise EmailSignInServiceError(
            "Failed to create sign-in API key.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(api_key_record)
    return tenant, workspace, api_key_record, raw_api_key, created_tenant, created_workspace
