"""Services for document upload and ingestion job lookup."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext
from app.config import get_settings
from app.core.storage import StorageError, delete_object, upload_bytes
from app.models import (
    Document,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    Namespace,
)


_SUPPORTED_UPLOAD_TYPES: Final[dict[str, str]] = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_GENERIC_CONTENT_TYPES: Final[set[str]] = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
}
_SAFE_FILENAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentServiceError(RuntimeError):
    """Raised when document service operations cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class DocumentUploadResult:
    """Domain result returned after a successful document upload."""

    document: Document
    ingestion_job: IngestionJob
    filename: str


def _normalize_filename(filename: str | None) -> tuple[str, str, str]:
    """Validate and normalize the uploaded filename."""

    raw_filename = (filename or "").strip()
    if not raw_filename:
        raise DocumentServiceError(
            "Uploaded file must include a filename.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    original_filename = Path(raw_filename).name
    if original_filename in {"", ".", ".."}:
        raise DocumentServiceError(
            "Uploaded file must include a valid filename.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    suffix = Path(original_filename).suffix.lower()
    if suffix not in _SUPPORTED_UPLOAD_TYPES:
        supported_suffixes = ", ".join(sorted(_SUPPORTED_UPLOAD_TYPES))
        raise DocumentServiceError(
            f"Unsupported file type. Allowed types: {supported_suffixes}.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    safe_filename = _SAFE_FILENAME_PATTERN.sub("-", original_filename).strip("-")
    if not safe_filename:
        safe_filename = f"document{suffix}"

    return original_filename, safe_filename, suffix


def _resolve_document_title(title: str | None, filename: str) -> str:
    """Resolve the stored document title from form input or filename."""

    if title is not None and title.strip():
        return title.strip()

    fallback_title = Path(filename).stem.strip()
    if fallback_title:
        return fallback_title
    return "Untitled document"


def _build_object_key(
    *,
    tenant_id: uuid.UUID,
    namespace_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
) -> str:
    """Build a stable tenant-scoped object key for the uploaded source file."""

    return (
        f"tenants/{tenant_id}/namespaces/{namespace_id}/documents/"
        f"{document_id}/source/{filename}"
    )


async def _get_namespace_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    namespace_id: uuid.UUID,
) -> Namespace:
    """Resolve a namespace only if it belongs to the authenticated tenant."""

    statement = select(Namespace).where(
        Namespace.tenant_id == tenant_id,
        Namespace.namespace_id == namespace_id,
    )
    result = await session.execute(statement)
    namespace = result.scalar_one_or_none()

    if namespace is None:
        raise DocumentServiceError(
            "Namespace not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return namespace


async def create_document_upload(
    *,
    session: AsyncSession,
    tenant_context: TenantContext,
    namespace_id: uuid.UUID,
    upload_file: UploadFile,
    title: str | None = None,
) -> DocumentUploadResult:
    """Store an uploaded source file and create the initial ingestion job."""

    await _get_namespace_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
        namespace_id=namespace_id,
    )

    provided_content_type = (upload_file.content_type or "").strip().lower()
    try:
        original_filename, safe_filename, suffix = _normalize_filename(upload_file.filename)
        payload = await upload_file.read()
    finally:
        await upload_file.close()

    if provided_content_type not in _GENERIC_CONTENT_TYPES and (
        provided_content_type != _SUPPORTED_UPLOAD_TYPES[suffix]
    ):
        raise DocumentServiceError(
            "Uploaded file content type does not match the file extension.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    if not payload:
        raise DocumentServiceError(
            "Uploaded file must not be empty.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    settings = get_settings()
    if len(payload) > settings.document_upload_max_bytes:
        raise DocumentServiceError(
            "Uploaded file exceeds the configured size limit.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    document_id = uuid.uuid4()
    job_id = uuid.uuid4()
    normalized_mime_type = _SUPPORTED_UPLOAD_TYPES[suffix]
    document_title = _resolve_document_title(title, original_filename)
    checksum = hashlib.sha256(payload).hexdigest()
    object_key = _build_object_key(
        tenant_id=tenant_context.tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        filename=safe_filename,
    )

    try:
        stored_object = await upload_bytes(
            object_key,
            payload,
            content_type=normalized_mime_type,
            metadata={
                "tenant_id": str(tenant_context.tenant_id),
                "namespace_id": str(namespace_id),
                "document_id": str(document_id),
                "checksum": checksum,
            },
        )
    except StorageError as exc:
        raise DocumentServiceError(
            "Failed to store uploaded file.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    document = Document(
        doc_id=document_id,
        tenant_id=tenant_context.tenant_id,
        namespace_id=namespace_id,
        object_key=stored_object.key,
        source_uri=f"s3://{stored_object.bucket}/{stored_object.key}",
        mime_type=normalized_mime_type,
        title=document_title,
        checksum=checksum,
        file_size_bytes=stored_object.size,
        status=DocumentStatus.UPLOADED,
    )
    ingestion_job = IngestionJob(
        job_id=job_id,
        tenant_id=tenant_context.tenant_id,
        doc_id=document_id,
        status=IngestionJobStatus.QUEUED,
    )
    session.add(document)
    session.add(ingestion_job)

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        try:
            await delete_object(stored_object.key)
        except StorageError:
            pass
        raise DocumentServiceError(
            "Failed to persist uploaded document metadata.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(document)
    await session.refresh(ingestion_job)

    return DocumentUploadResult(
        document=document,
        ingestion_job=ingestion_job,
        filename=original_filename,
    )


async def get_ingestion_job_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> IngestionJob:
    """Return a tenant-scoped ingestion job or raise if it does not exist."""

    statement = select(IngestionJob).where(
        IngestionJob.tenant_id == tenant_id,
        IngestionJob.job_id == job_id,
    )
    result = await session.execute(statement)
    ingestion_job = result.scalar_one_or_none()

    if ingestion_job is None:
        raise DocumentServiceError(
            "Ingestion job not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return ingestion_job
