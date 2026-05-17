"""Health and readiness routes."""

from fastapi import APIRouter, Request, Response, status

from app.core.database import ping_database
from app.core.storage import ensure_storage_ready
from app.schemas.health import HealthCheckResponse, ReadinessResponse


router = APIRouter()


@router.get("/health/live", response_model=HealthCheckResponse)
async def live() -> HealthCheckResponse:
    """Report process liveness."""

    return HealthCheckResponse(status="alive")


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(request: Request, response: Response) -> ReadinessResponse:
    """Report service readiness and dependency health."""

    settings = request.app.state.settings
    database_ready = await ping_database()
    storage_ready = await ensure_storage_ready()
    checks = {
        "config": "ok",
        "database": "ok" if database_ready else "error",
        "storage": "ok" if storage_ready else "error",
    }
    is_ready = database_ready and storage_ready
    response.status_code = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        checks=checks,
    )
