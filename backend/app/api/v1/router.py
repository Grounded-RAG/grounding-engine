"""Top-level API router for the backend."""

from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.capabilities import router as capabilities_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.query import router as query_router
from app.api.v1.runs import router as runs_router
from app.api.v1.team_members import router as team_members_router
from app.api.v1.workspaces import router as workspaces_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(agents_router, prefix="/v1", tags=["agents"])
api_router.include_router(api_keys_router, prefix="/v1", tags=["api-keys"])
api_router.include_router(audit_logs_router, prefix="/v1", tags=["governance"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(billing_router, prefix="/v1", tags=["billing"])
api_router.include_router(capabilities_router, prefix="/v1", tags=["capabilities"])
api_router.include_router(conversations_router, prefix="/v1", tags=["conversations"])
api_router.include_router(dashboard_router, prefix="/v1", tags=["dashboard"])
api_router.include_router(datasets_router, prefix="/v1", tags=["datasets"])
api_router.include_router(documents_router, prefix="/v1", tags=["documents"])
api_router.include_router(invitations_router, prefix="/v1", tags=["invitations"])
api_router.include_router(query_router, prefix="/v1", tags=["query"])
api_router.include_router(runs_router, prefix="/v1", tags=["runs"])
api_router.include_router(team_members_router, prefix="/v1", tags=["team-members"])
api_router.include_router(workspaces_router, prefix="/v1", tags=["workspaces"])
