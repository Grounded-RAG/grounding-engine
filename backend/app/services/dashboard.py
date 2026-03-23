"""Dashboard aggregation services for the product shell."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Agent,
    Conversation,
    Document,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    Namespace,
)
from app.schemas.dashboard import DashboardRecentJobResponse, DashboardSummaryResponse
from app.schemas.runs import RunResponse
from app.services.runs import list_runs_for_tenant


async def _count_rows(
    *,
    session: AsyncSession,
    model,
    tenant_id: uuid.UUID,
    conditions: tuple = (),
) -> int:
    """Return a tenant-scoped row count for one model."""

    statement = select(func.count()).select_from(model).where(
        model.tenant_id == tenant_id,
        *conditions,
    )
    result = await session.execute(statement)
    return int(result.scalar_one())


async def get_dashboard_summary_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> DashboardSummaryResponse:
    """Return top-level dashboard counts for one tenant."""

    return DashboardSummaryResponse(
        dataset_count=await _count_rows(
            session=session,
            model=Namespace,
            tenant_id=tenant_id,
        ),
        document_count=await _count_rows(
            session=session,
            model=Document,
            tenant_id=tenant_id,
        ),
        indexed_document_count=await _count_rows(
            session=session,
            model=Document,
            tenant_id=tenant_id,
            conditions=(Document.status == DocumentStatus.INDEXED,),
        ),
        running_job_count=await _count_rows(
            session=session,
            model=IngestionJob,
            tenant_id=tenant_id,
            conditions=(IngestionJob.status == IngestionJobStatus.RUNNING,),
        ),
        failed_job_count=await _count_rows(
            session=session,
            model=IngestionJob,
            tenant_id=tenant_id,
            conditions=(IngestionJob.status == IngestionJobStatus.FAILED,),
        ),
        agent_count=await _count_rows(
            session=session,
            model=Agent,
            tenant_id=tenant_id,
        ),
        conversation_count=await _count_rows(
            session=session,
            model=Conversation,
            tenant_id=tenant_id,
        ),
    )


async def list_recent_runs_for_dashboard(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
) -> list[RunResponse]:
    """Return recent runs for dashboard activity views."""

    return await list_runs_for_tenant(
        session=session,
        tenant_id=tenant_id,
        limit=limit,
    )


async def list_recent_jobs_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
) -> list[DashboardRecentJobResponse]:
    """Return recent ingestion jobs with enough context for dashboard activity."""

    statement = (
        select(
            IngestionJob,
            Document.namespace_id.label("dataset_id"),
            Document.title.label("document_title"),
        )
        .join(
            Document,
            and_(
                IngestionJob.tenant_id == Document.tenant_id,
                IngestionJob.doc_id == Document.doc_id,
            ),
        )
        .where(IngestionJob.tenant_id == tenant_id)
        .order_by(IngestionJob.created_at.desc(), IngestionJob.job_id.desc())
        .limit(limit)
    )
    result = await session.execute(statement)

    jobs: list[DashboardRecentJobResponse] = []
    for job, dataset_id, document_title in result.all():
        jobs.append(
            DashboardRecentJobResponse(
                job_id=job.job_id,
                document_id=job.doc_id,
                dataset_id=dataset_id,
                document_title=document_title,
                status=job.status,
                attempt_count=job.attempt_count,
                error_code=job.error_code,
                error_detail=job.error_detail,
                started_at=job.started_at,
                completed_at=job.completed_at,
                created_at=job.created_at,
            )
        )
    return jobs
