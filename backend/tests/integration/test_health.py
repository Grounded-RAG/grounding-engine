"""Integration tests for basic application endpoints."""

from fastapi.testclient import TestClient


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


def test_ready_health_endpoint(client: TestClient) -> None:
    """Readiness endpoint should report config readiness."""

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "Grounded Backend",
        "environment": "development",
        "version": "0.1.0",
        "checks": {"config": "ok"},
    }
