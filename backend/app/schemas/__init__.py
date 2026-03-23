"""API schema package."""

from app.schemas.agents import (
    AgentChatRequest,
    AgentChatResponse,
    AgentCreateRequest,
    AgentDatasetAttachRequest,
    AgentResponse,
    AgentUpdateRequest,
)
from app.schemas.api_keys import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyResponse
from app.schemas.auth import AuthSmokeResponse
from app.schemas.capabilities import (
    CapabilitiesResponse,
    FeatureCapabilityResponse,
    ModeCapabilityResponse,
)
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
)
from app.schemas.dashboard import DashboardRecentJobResponse, DashboardSummaryResponse
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
from app.schemas.messages import MessageResponse
from app.schemas.query import CitationResponse, GroundedAnswerResponse, QueryRequest
from app.schemas.runs import RunResponse
from app.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)

__all__ = [
    "AuthSmokeResponse",
    "AgentChatRequest",
    "AgentChatResponse",
    "AgentCreateRequest",
    "AgentDatasetAttachRequest",
    "AgentResponse",
    "AgentUpdateRequest",
    "APIKeyCreateRequest",
    "APIKeyCreateResponse",
    "APIKeyResponse",
    "CapabilitiesResponse",
    "CitationResponse",
    "ConversationCreateRequest",
    "ConversationResponse",
    "ConversationUpdateRequest",
    "DashboardRecentJobResponse",
    "DashboardSummaryResponse",
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
    "MessageResponse",
    "QueryRequest",
    "ReadinessResponse",
    "RunResponse",
    "WorkspaceCreateRequest",
    "WorkspaceResponse",
    "WorkspaceUpdateRequest",
]
