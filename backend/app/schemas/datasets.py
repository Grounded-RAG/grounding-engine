"""Dataset API schemas built on top of the namespace storage model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    DocumentStatus,
    ExecutionTier,
    FreshnessProfile,
    IngestionJobStatus,
    SensitivityLevel,
)


class DatasetCreateRequest(BaseModel):
    """Request used to create one product-facing dataset."""

    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(default="general", min_length=1, max_length=100)
    sensitivity_level: SensitivityLevel = SensitivityLevel.INTERNAL
    freshness_profile: FreshnessProfile = FreshnessProfile.BALANCED
    min_execution_tier: ExecutionTier = ExecutionTier.STANDARD
    allow_web_fallback: bool = False
    allow_internal_model_retrieval: bool = False


class DatasetUpdateRequest(BaseModel):
    """Patch request for one tenant-scoped dataset."""

    workspace_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    sensitivity_level: SensitivityLevel | None = None
    freshness_profile: FreshnessProfile | None = None
    min_execution_tier: ExecutionTier | None = None
    allow_web_fallback: bool | None = None
    allow_internal_model_retrieval: bool | None = None


class DatasetResponse(BaseModel):
    """Product-facing dataset response shape."""

    dataset_id: UUID
    workspace_id: UUID | None
    name: str
    domain: str
    sensitivity_level: SensitivityLevel
    freshness_profile: FreshnessProfile
    min_execution_tier: ExecutionTier
    allow_web_fallback: bool
    allow_internal_model_retrieval: bool
    created_at: datetime


class DatasetDocumentResponse(BaseModel):
    """Summary of one document belonging to a dataset."""

    document_id: UUID
    dataset_id: UUID
    title: str | None
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    created_at: datetime


class DatasetIngestionJobResponse(BaseModel):
    """Summary of one ingestion job belonging to a dataset."""

    job_id: UUID
    document_id: UUID
    dataset_id: UUID
    status: IngestionJobStatus
    attempt_count: int
    error_code: str | None
    error_detail: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DatasetUploadResponse(BaseModel):
    """Response returned after uploading into one dataset."""

    dataset_id: UUID
    document_id: UUID
    job_id: UUID
    filename: str
    title: str
    mime_type: str
    file_size_bytes: int
    document_status: DocumentStatus
    job_status: IngestionJobStatus
