"""Dataset routes built on top of the namespace storage model."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from arq import create_pool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.config import get_settings
from app.core.database import get_db_session
from app.core.rate_limit import default_rate_limit, ingest_rate_limit
from app.schemas.datasets import (
    DatasetCreateRequest,
    DatasetDocumentResponse,
    DatasetIngestionJobResponse,
    DatasetResponse,
    DatasetUpdateRequest,
    DatasetUploadResponse,
)
from app.services.datasets import (
    DatasetServiceError,
    create_dataset,
    get_dataset_for_tenant,
    list_dataset_documents,
    list_dataset_ingestion_jobs,
    list_datasets_for_tenant,
    update_dataset,
)
from app.services.documents import DocumentServiceError, create_document_upload
from app.worker_settings import get_redis_settings


router = APIRouter()


def _build_dataset_response(dataset) -> DatasetResponse:
    """Map one namespace row into the product-facing dataset schema."""

    return DatasetResponse(
        dataset_id=dataset.namespace_id,
        workspace_id=dataset.workspace_id,
        name=dataset.name,
        domain=dataset.domain,
        sensitivity_level=dataset.sensitivity_level,
        freshness_profile=dataset.freshness_profile,
        min_execution_tier=dataset.min_execution_tier,
        allow_web_fallback=dataset.allow_web_fallback,
        allow_internal_model_retrieval=dataset.allow_internal_model_retrieval,
        created_at=dataset.created_at,
    )


@router.post(
    "/datasets",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset_route(
    dataset_request: DatasetCreateRequest = Body(...),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(default_rate_limit),
) -> DatasetResponse:
    """Create one dataset for the authenticated tenant."""

    try:
        dataset = await create_dataset(
            session=session,
            tenant_id=tenant_context.tenant_id,
            dataset_request=dataset_request,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_dataset_response(dataset)


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets_route(
    workspace_id: UUID | None = Query(default=None),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[DatasetResponse]:
    """List datasets owned by the authenticated tenant."""

    try:
        datasets = await list_datasets_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return [_build_dataset_response(dataset) for dataset in datasets]


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_route(
    dataset_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    """Return one dataset only if it belongs to the authenticated tenant."""

    try:
        dataset = await get_dataset_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            dataset_id=dataset_id,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_dataset_response(dataset)


@router.patch("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset_route(
    dataset_id: UUID,
    dataset_request: DatasetUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    """Patch one dataset owned by the authenticated tenant."""

    try:
        dataset = await update_dataset(
            session=session,
            tenant_id=tenant_context.tenant_id,
            dataset_id=dataset_id,
            dataset_request=dataset_request,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_dataset_response(dataset)


@router.get(
    "/datasets/{dataset_id}/documents",
    response_model=list[DatasetDocumentResponse],
)
async def list_dataset_documents_route(
    dataset_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[DatasetDocumentResponse]:
    """List documents belonging to one dataset."""

    try:
        documents = await list_dataset_documents(
            session=session,
            tenant_id=tenant_context.tenant_id,
            dataset_id=dataset_id,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return [
        DatasetDocumentResponse(
            document_id=document.doc_id,
            dataset_id=document.namespace_id,
            title=document.title,
            mime_type=document.mime_type,
            file_size_bytes=document.file_size_bytes,
            status=document.status,
            created_at=document.created_at,
        )
        for document in documents
    ]


@router.get(
    "/datasets/{dataset_id}/ingestion-jobs",
    response_model=list[DatasetIngestionJobResponse],
)
async def list_dataset_ingestion_jobs_route(
    dataset_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[DatasetIngestionJobResponse]:
    """List ingestion jobs belonging to one dataset."""

    try:
        jobs = await list_dataset_ingestion_jobs(
            session=session,
            tenant_id=tenant_context.tenant_id,
            dataset_id=dataset_id,
        )
    except DatasetServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    dataset = await get_dataset_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
        dataset_id=dataset_id,
    )

    return [
        DatasetIngestionJobResponse(
            job_id=job.job_id,
            document_id=job.doc_id,
            dataset_id=dataset.namespace_id,
            status=job.status,
            attempt_count=job.attempt_count,
            error_code=job.error_code,
            error_detail=job.error_detail,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
        )
        for job in jobs
    ]


@router.post(
    "/datasets/{dataset_id}/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset_document_route(
    response: Response,
    dataset_id: UUID,
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(ingest_rate_limit),
) -> DatasetUploadResponse:
    """Upload one source file into a dataset and start ingestion."""

    try:
        result = await create_document_upload(
            session=session,
            tenant_context=tenant_context,
            namespace_id=dataset_id,
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


    return DatasetUploadResponse(
        dataset_id=result.document.namespace_id,
        document_id=result.document.doc_id,
        job_id=result.ingestion_job.job_id,
        filename=result.filename,
        title=result.document.title,
        mime_type=result.document.mime_type,
        file_size_bytes=result.document.file_size_bytes,
        document_status=result.document.status,
        job_status=result.ingestion_job.status,
        already_exists=result.already_exists,
    )
