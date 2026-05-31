"""Document upload and ingestion job routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from arq import create_pool

from app.api.deps import TenantContext, get_tenant_context
from app.config import get_settings
from app.core.database import get_db_session
from app.models import Namespace
from app.schemas.documents import (
    DocumentReindexResponse,
    DocumentUploadResponse,
    IngestionJobStatusResponse,
)
from app.services.documents import (
    DocumentServiceError,
    create_document_upload,
    get_ingestion_job_for_tenant,
    reindex_document_for_tenant,
)
from app.services.audit_logs import write_audit_log
from app.worker_settings import get_redis_settings

router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    response: Response,
    namespace_id: UUID = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """Persist an uploaded file and create the initial ingestion job."""

    try:
        result = await create_document_upload(
            session=session,
            tenant_context=tenant_context,
            namespace_id=namespace_id,
            upload_file=file,
            title=title,
        )
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if result.already_exists:
        response.status_code = status.HTTP_200_OK

    if get_settings().ingestion_autorun_enabled and result.should_schedule_ingestion:
        redis_pool = await create_pool(get_redis_settings())
        await redis_pool.enqueue_job("ingest_document", str(result.ingestion_job.job_id))
        await redis_pool.aclose()

    namespace_result = await session.execute(
        select(Namespace).where(
            Namespace.tenant_id == tenant_context.tenant_id,
            Namespace.namespace_id == namespace_id,
        )
    )
    namespace = namespace_result.scalar_one_or_none()
    workspace_id = namespace.workspace_id if namespace is not None else None

    await write_audit_log(
        session=session,
        tenant_id=tenant_context.tenant_id,
        actor_key_id=tenant_context.api_key_id,
        workspace_id=workspace_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=str(result.document.doc_id),
        summary=f"Document '{result.filename}' uploaded",
    )

    return DocumentUploadResponse(
        document_id=result.document.doc_id,
        namespace_id=result.document.namespace_id,
        job_id=result.ingestion_job.job_id,
        filename=result.filename,
        title=result.document.title,
        mime_type=result.document.mime_type,
        file_size_bytes=result.document.file_size_bytes,
        document_status=result.document.status,
        job_status=result.ingestion_job.status,
        already_exists=result.already_exists,
    )


@router.get(
    "/ingestion-jobs/{job_id}",
    response_model=IngestionJobStatusResponse,
)
async def get_ingestion_job_status(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobStatusResponse:
    """Return the tenant-scoped status for an ingestion job."""

    try:
        ingestion_job = await get_ingestion_job_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            job_id=job_id,
        )
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return IngestionJobStatusResponse(
        job_id=ingestion_job.job_id,
        document_id=ingestion_job.doc_id,
        status=ingestion_job.status,
        attempt_count=ingestion_job.attempt_count,
        error_code=ingestion_job.error_code,
        error_detail=ingestion_job.error_detail,
        started_at=ingestion_job.started_at,
        completed_at=ingestion_job.completed_at,
        created_at=ingestion_job.created_at,
    )


@router.post(
    "/documents/{document_id}/reindex",
    response_model=DocumentReindexResponse,
)
async def reindex_document_route(
    document_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentReindexResponse:
    """Queue one existing document for a fresh Standard ingestion run."""

    try:
        result = await reindex_document_for_tenant(
            session=session,
            tenant_context=tenant_context,
            document_id=document_id,
        )
    except DocumentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if get_settings().ingestion_autorun_enabled and result.should_schedule_ingestion:
        redis_pool = await create_pool(get_redis_settings())
        await redis_pool.enqueue_job("ingest_document", str(result.ingestion_job.job_id))
        await redis_pool.aclose()

    return DocumentReindexResponse(
        document_id=result.document.doc_id,
        namespace_id=result.document.namespace_id,
        job_id=result.ingestion_job.job_id,
        document_status=result.document.status,
        job_status=result.ingestion_job.status,
    )
