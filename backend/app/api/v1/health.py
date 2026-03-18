"""Health and readiness routes."""

from fastapi import APIRouter, Request

from app.schemas.health import HealthCheckResponse, ReadinessResponse


router = APIRouter()


@router.get("/health/live", response_model=HealthCheckResponse)
async def live() -> HealthCheckResponse:
    """Report process liveness."""

    return HealthCheckResponse(status="alive")


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> ReadinessResponse:
    """Report service readiness and loaded configuration state."""

    settings = request.app.state.settings
    return ReadinessResponse(
        status="ready",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        checks={"config": "ok"},
    )
