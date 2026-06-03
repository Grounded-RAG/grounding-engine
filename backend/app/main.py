"""FastAPI application entrypoint for the Grounded backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.core.telemetry import configure_logging, get_logger, request_context_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load application settings during startup."""

    app.state.settings = get_settings()
    logger = get_logger("app.lifecycle")
    logger.info(
        "application_startup",
        service=app.state.settings.app_name,
        environment=app.state.settings.app_env,
        version=app.state.settings.app_version,
    )
    for warning in app.state.settings.startup_warnings():
        logger.warning("startup_warning", detail=warning)
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Trace-Id", "X-Run-Id", "X-Request-Id"],
        )
    app.middleware("http")(request_context_middleware)
    app.include_router(api_router)

    def root_payload() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "environment": settings.app_env,
            "version": settings.app_version,
            "status": "ok",
            "api_base_url": str(settings.api_base_url),
            "docs": "/docs",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
        }

    @app.get("/", tags=["meta"])
    async def root(request: Request):
        """Return service metadata (JSON) or a simple HTML status page."""

        payload = root_payload()
        accept = request.headers.get("accept", "")
        if "text/html" in accept and "application/json" not in accept.split(",")[0]:
            api_base = payload["api_base_url"]
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{payload["service"]}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    .meta {{ color: #555; margin-bottom: 1.5rem; }}
    .ok {{ color: #0d7a3e; font-weight: 600; }}
    ul {{ line-height: 1.8; padding-left: 1.25rem; }}
    a {{ color: #1d4ed8; }}
    code {{ background: #f4f4f5; padding: 0.1rem 0.35rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{payload["service"]}</h1>
  <p class="meta">Environment: <code>{payload["environment"]}</code> · Version: <code>{payload["version"]}</code></p>
  <p class="ok">API is running</p>
  <p>Base URL: <code>{api_base}</code></p>
  <ul>
    <li><a href="/docs">API documentation (Swagger)</a></li>
    <li><a href="/health/live">Liveness check</a></li>
    <li><a href="/health/ready">Readiness check</a></li>
  </ul>
</body>
</html>"""
            return HTMLResponse(html)

        return payload

    return app


app = create_app()
