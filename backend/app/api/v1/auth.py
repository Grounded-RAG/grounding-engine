"""Authentication route placeholders."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/auth/smoke")
async def auth_smoke() -> dict[str, str]:
    """Temporary authenticated smoke route placeholder."""

    return {"status": "pending-auth"}
