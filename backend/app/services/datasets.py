"""Dataset product APIs built on top of the namespace storage model."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, IngestionJob, Namespace, Workspace
from app.schemas.datasets import DatasetCreateRequest, DatasetUpdateRequest


class DatasetServiceError(RuntimeError):
    """Raised when a dataset operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _normalize_dataset_name(name: str) -> str:
    """Normalize a dataset name while rejecting blank values."""

    normalized = name.strip()
    if not normalized:
        raise DatasetServiceError(
            "Dataset name must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def _normalize_domain(domain: str) -> str:
    """Normalize dataset domain values while rejecting blank values."""

    normalized = domain.strip()
    if not normalized:
        raise DatasetServiceError(
            "Dataset domain must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


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
        raise DatasetServiceError(
            "Workspace not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return workspace


async def _get_dataset_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> Namespace:
    """Resolve one dataset only if it belongs to the authenticated tenant."""

    statement = select(Namespace).where(
        Namespace.tenant_id == tenant_id,
        Namespace.namespace_id == dataset_id,
    )
    result = await session.execute(statement)
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise DatasetServiceError(
            "Dataset not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return dataset


async def _ensure_dataset_name_is_unique(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    exclude_dataset_id: uuid.UUID | None = None,
) -> None:
    """Ensure dataset names remain unique per tenant."""

    statement = select(Namespace).where(
        Namespace.tenant_id == tenant_id,
        Namespace.name == name,
    )
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()
    if existing is None:
        return
    if exclude_dataset_id is not None and existing.namespace_id == exclude_dataset_id:
        return
    raise DatasetServiceError(
        "Dataset name already exists for tenant.",
        status_code=status.HTTP_409_CONFLICT,
    )


async def create_dataset(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_request: DatasetCreateRequest,
) -> Namespace:
    """Create one product-facing dataset backed by a namespace row."""

    await _get_workspace_for_tenant(
        session=session,
        tenant_id=tenant_id,
        workspace_id=dataset_request.workspace_id,
    )

    name = _normalize_dataset_name(dataset_request.name)
    domain = _normalize_domain(dataset_request.domain)

    await _ensure_dataset_name_is_unique(
        session=session,
        tenant_id=tenant_id,
        name=name,
    )

    dataset = Namespace(
        namespace_id=uuid.uuid4(),
        tenant_id=tenant_id,
        workspace_id=dataset_request.workspace_id,
        name=name,
        domain=domain,
        sensitivity_level=dataset_request.sensitivity_level,
        freshness_profile=dataset_request.freshness_profile,
        min_execution_tier=dataset_request.min_execution_tier,
        allow_web_fallback=dataset_request.allow_web_fallback,
        allow_internal_model_retrieval=dataset_request.allow_internal_model_retrieval,
    )
    session.add(dataset)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise DatasetServiceError(
            "Failed to create dataset.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(dataset)
    return dataset


async def list_datasets_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID | None = None,
) -> list[Namespace]:
    """List datasets owned by the authenticated tenant."""

    if workspace_id is not None:
        await _get_workspace_for_tenant(
            session=session,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
        )

    statement = select(Namespace).where(Namespace.tenant_id == tenant_id)
    if workspace_id is not None:
        statement = statement.where(Namespace.workspace_id == workspace_id)
    statement = statement.order_by(Namespace.created_at.asc(), Namespace.namespace_id.asc())
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_dataset_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> Namespace:
    """Return one tenant-scoped dataset."""

    return await _get_dataset_for_tenant(
        session=session,
        tenant_id=tenant_id,
        dataset_id=dataset_id,
    )


async def update_dataset(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID,
    dataset_request: DatasetUpdateRequest,
) -> Namespace:
    """Patch one dataset row owned by the authenticated tenant."""

    dataset = await _get_dataset_for_tenant(
        session=session,
        tenant_id=tenant_id,
        dataset_id=dataset_id,
    )

    fields_set = dataset_request.model_fields_set

    if "workspace_id" in fields_set and dataset_request.workspace_id is not None:
        await _get_workspace_for_tenant(
            session=session,
            tenant_id=tenant_id,
            workspace_id=dataset_request.workspace_id,
        )
        dataset.workspace_id = dataset_request.workspace_id

    if "name" in fields_set and dataset_request.name is not None:
        name = _normalize_dataset_name(dataset_request.name)
        await _ensure_dataset_name_is_unique(
            session=session,
            tenant_id=tenant_id,
            name=name,
            exclude_dataset_id=dataset.namespace_id,
        )
        dataset.name = name

    if "domain" in fields_set and dataset_request.domain is not None:
        dataset.domain = _normalize_domain(dataset_request.domain)

    if "sensitivity_level" in fields_set and dataset_request.sensitivity_level is not None:
        dataset.sensitivity_level = dataset_request.sensitivity_level
    if "freshness_profile" in fields_set and dataset_request.freshness_profile is not None:
        dataset.freshness_profile = dataset_request.freshness_profile
    if "min_execution_tier" in fields_set and dataset_request.min_execution_tier is not None:
        dataset.min_execution_tier = dataset_request.min_execution_tier
    if "allow_web_fallback" in fields_set and dataset_request.allow_web_fallback is not None:
        dataset.allow_web_fallback = dataset_request.allow_web_fallback
    if (
        "allow_internal_model_retrieval" in fields_set
        and dataset_request.allow_internal_model_retrieval is not None
    ):
        dataset.allow_internal_model_retrieval = (
            dataset_request.allow_internal_model_retrieval
        )

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise DatasetServiceError(
            "Failed to update dataset.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(dataset)
    return dataset


async def list_dataset_documents(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> list[Document]:
    """List documents belonging to one tenant-scoped dataset."""

    await _get_dataset_for_tenant(
        session=session,
        tenant_id=tenant_id,
        dataset_id=dataset_id,
    )

    statement = (
        select(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.namespace_id == dataset_id,
        )
        .order_by(Document.created_at.desc(), Document.doc_id.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def list_dataset_ingestion_jobs(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> list[IngestionJob]:
    """List ingestion jobs for documents in one tenant-scoped dataset."""

    await _get_dataset_for_tenant(
        session=session,
        tenant_id=tenant_id,
        dataset_id=dataset_id,
    )

    statement = (
        select(IngestionJob)
        .join(
            Document,
            and_(
                IngestionJob.tenant_id == Document.tenant_id,
                IngestionJob.doc_id == Document.doc_id,
            ),
        )
        .where(
            Document.tenant_id == tenant_id,
            Document.namespace_id == dataset_id,
        )
        .order_by(IngestionJob.created_at.desc(), IngestionJob.job_id.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
