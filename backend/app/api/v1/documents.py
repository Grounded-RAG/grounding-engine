"""Document upload and ingestion job routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.documents import DocumentUploadResponse, IngestionJobStatusResponse
from app.services.documents import (
    DocumentServiceError,
    create_document_upload,
    get_ingestion_job_for_tenant,
)

router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
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
