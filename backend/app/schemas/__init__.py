"""API schema package."""

from app.schemas.auth import AuthSmokeResponse
from app.schemas.capabilities import (
    CapabilitiesResponse,
    FeatureCapabilityResponse,
    ModeCapabilityResponse,
)
from app.schemas.datasets import (
    DatasetCreateRequest,
    DatasetDocumentResponse,
    DatasetIngestionJobResponse,
    DatasetResponse,
    DatasetUpdateRequest,
    DatasetUploadResponse,
)
from app.schemas.documents import DocumentUploadResponse, IngestionJobStatusResponse
from app.schemas.health import HealthCheckResponse, ReadinessResponse
from app.schemas.query import CitationResponse, GroundedAnswerResponse, QueryRequest
from app.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)

__all__ = [
    "AuthSmokeResponse",
    "CapabilitiesResponse",
    "CitationResponse",
    "DatasetCreateRequest",
    "DatasetDocumentResponse",
    "DatasetIngestionJobResponse",
    "DatasetResponse",
    "DatasetUpdateRequest",
    "DatasetUploadResponse",
    "DocumentUploadResponse",
    "FeatureCapabilityResponse",
    "GroundedAnswerResponse",
    "HealthCheckResponse",
    "IngestionJobStatusResponse",
    "ModeCapabilityResponse",
    "QueryRequest",
    "ReadinessResponse",
    "WorkspaceCreateRequest",
    "WorkspaceResponse",
    "WorkspaceUpdateRequest",
]
