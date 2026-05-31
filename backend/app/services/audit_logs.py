"""Audit log service — write and query immutable audit entries."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry import get_logger
from app.models.audit_log import AuditLog

logger = get_logger("app.audit_logs")


async def write_audit_log(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    action: str,
    resource_type: str,
    workspace_id: uuid.UUID | None = None,
    actor_key_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    summary: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        log_id=uuid.uuid4(),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        actor_key_id=actor_key_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        metadata_=metadata,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def list_audit_logs(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    filters = [AuditLog.tenant_id == tenant_id]
    if workspace_id is not None:
        filters.append(AuditLog.workspace_id == workspace_id)

    count_result = await session.execute(
        select(func.count()).select_from(AuditLog).where(*filters)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    rows_result = await session.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return list(rows_result.scalars().all()), total
