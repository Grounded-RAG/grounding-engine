"""Top-level API router for the backend."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.capabilities import router as capabilities_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/v1", tags=["auth"])
api_router.include_router(capabilities_router, prefix="/v1", tags=["capabilities"])
api_router.include_router(documents_router, prefix="/v1", tags=["documents"])
api_router.include_router(query_router, prefix="/v1", tags=["query"])
