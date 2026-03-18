"""FastAPI application entrypoint for the Grounded backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load application settings during startup."""

    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        """Return basic service metadata."""

        return {
            "service": settings.app_name,
            "environment": settings.app_env,
            "version": settings.app_version,
        }

    return app


app = create_app()
