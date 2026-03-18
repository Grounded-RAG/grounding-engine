"""Integration tests for basic application endpoints."""

from fastapi.testclient import TestClient

from app.api.v1 import health as health_module


def test_root_returns_service_metadata(client: TestClient) -> None:
    """Root endpoint should expose basic service metadata."""

    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "Grounded Backend"
    assert payload["environment"] == "development"
    assert payload["version"] == "0.1.0"


def test_live_health_endpoint(client: TestClient) -> None:
    """Liveness endpoint should report alive."""

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_health_endpoint_reports_dependency_status(
    client: TestClient,
    monkeypatch,
) -> None:
    """Readiness endpoint should report dependency readiness."""

    async def database_ready() -> bool:
        return True

    async def storage_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "ping_database", database_ready)
    monkeypatch.setattr(health_module, "ensure_storage_ready", storage_ready)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "Grounded Backend",
        "environment": "development",
        "version": "0.1.0",
        "checks": {
            "config": "ok",
            "database": "ok",
            "storage": "ok",
        },
    }


def test_ready_health_endpoint_returns_503_when_dependency_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    """Readiness endpoint should fail closed when a dependency is unavailable."""

    async def database_not_ready() -> bool:
        return False

    async def storage_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "ping_database", database_not_ready)
    monkeypatch.setattr(health_module, "ensure_storage_ready", storage_ready)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "Grounded Backend",
        "environment": "development",
        "version": "0.1.0",
        "checks": {
            "config": "ok",
            "database": "error",
            "storage": "ok",
        },
    }
