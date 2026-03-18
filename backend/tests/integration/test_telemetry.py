"""Integration tests for request telemetry and request IDs."""

from fastapi.testclient import TestClient

from app.core.telemetry import REQUEST_ID_HEADER


def test_request_id_header_is_added_to_responses(client: TestClient) -> None:
    """Every request should receive a request ID header."""

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]


def test_request_id_header_is_preserved_when_provided(client: TestClient) -> None:
    """Caller-supplied request IDs should be returned unchanged."""

    response = client.get(
        "/health/live",
        headers={REQUEST_ID_HEADER: "req-test-123"},
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-test-123"
