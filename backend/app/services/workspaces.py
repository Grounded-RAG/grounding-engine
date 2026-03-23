"""Workspace CRUD services for the product shell."""

from __future__ import annotations

import re
import uuid

from fastapi import status
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workspace
from app.schemas.workspaces import WorkspaceCreateRequest, WorkspaceUpdateRequest


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class WorkspaceServiceError(RuntimeError):
    """Raised when a workspace operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _normalize_name(name: str) -> str:
    """Normalize a workspace name while rejecting blank values."""

    normalized = name.strip()
    if not normalized:
        raise WorkspaceServiceError(
            "Workspace name must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def _normalize_description(description: str | None) -> str | None:
    """Normalize workspace descriptions and allow explicit clearing."""

    if description is None:
        return None
    normalized = description.strip()
    return normalized or None


def _slugify(value: str) -> str:
    """Build a stable slug from a name or user-provided slug."""

    normalized = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    if not normalized:
        raise WorkspaceServiceError(
            "Workspace slug must include letters or numbers.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized[:120]


async def _get_workspace_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace:
    """Resolve one workspace only if it belongs to the authenticated tenant."""

    statement = select(Workspace).where(
        Workspace.tenant_id == tenant_id,
        Workspace.workspace_id == workspace_id,
    )
    result = await session.execute(statement)
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceServiceError(
            "Workspace not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return workspace


async def _ensure_workspace_uniqueness(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    slug: str,
    exclude_workspace_id: uuid.UUID | None = None,
) -> None:
    """Ensure one tenant does not reuse a workspace name or slug."""

    statement = select(Workspace).where(
        Workspace.tenant_id == tenant_id,
        or_(Workspace.name == name, Workspace.slug == slug),
    )
    result = await session.execute(statement)
    existing = result.scalars().all()

    for workspace in existing:
        if exclude_workspace_id is not None and workspace.workspace_id == exclude_workspace_id:
            continue
        if workspace.name == name:
            raise WorkspaceServiceError(
                "Workspace name already exists for tenant.",
                status_code=status.HTTP_409_CONFLICT,
            )
        if workspace.slug == slug:
            raise WorkspaceServiceError(
                "Workspace slug already exists for tenant.",
                status_code=status.HTTP_409_CONFLICT,
            )


async def create_workspace(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_request: WorkspaceCreateRequest,
) -> Workspace:
    """Create one workspace for the authenticated tenant."""

    name = _normalize_name(workspace_request.name)
    slug = _slugify(workspace_request.slug or name)
    description = _normalize_description(workspace_request.description)

    await _ensure_workspace_uniqueness(
        session=session,
        tenant_id=tenant_id,
        name=name,
        slug=slug,
    )

    workspace = Workspace(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        description=description,
    )
    session.add(workspace)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise WorkspaceServiceError(
            "Failed to create workspace.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(workspace)
    return workspace


async def list_workspaces_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[Workspace]:
    """Return all workspaces owned by the authenticated tenant."""

    statement = (
        select(Workspace)
        .where(Workspace.tenant_id == tenant_id)
        .order_by(Workspace.created_at.asc(), Workspace.workspace_id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_workspace_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace:
    """Return one tenant-scoped workspace."""

    return await _get_workspace_for_tenant(
        session=session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )


async def update_workspace(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID,
    workspace_request: WorkspaceUpdateRequest,
) -> Workspace:
    """Patch one tenant-scoped workspace."""

    workspace = await _get_workspace_for_tenant(
        session=session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )

    fields_set = workspace_request.model_fields_set
    next_name = workspace.name
    next_slug = workspace.slug

    if "name" in fields_set and workspace_request.name is not None:
        next_name = _normalize_name(workspace_request.name)
    if "slug" in fields_set and workspace_request.slug is not None:
        next_slug = _slugify(workspace_request.slug)

    if next_name != workspace.name or next_slug != workspace.slug:
        await _ensure_workspace_uniqueness(
            session=session,
            tenant_id=tenant_id,
            name=next_name,
            slug=next_slug,
            exclude_workspace_id=workspace.workspace_id,
        )

    if "name" in fields_set and workspace_request.name is not None:
        workspace.name = next_name
    if "slug" in fields_set and workspace_request.slug is not None:
        workspace.slug = next_slug
    if "description" in fields_set:
        workspace.description = _normalize_description(workspace_request.description)

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise WorkspaceServiceError(
            "Failed to update workspace.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(workspace)
    return workspace
