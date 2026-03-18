"""Health route placeholders."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    """Return a simple liveness response."""

    return {"status": "alive"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    """Return a simple readiness response."""

    return {"status": "ready"}
