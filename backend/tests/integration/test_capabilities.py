"""Route-level tests for the capabilities endpoint."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_tenant_context
from app.main import create_app


def test_capabilities_endpoint_returns_mode_and_feature_availability() -> None:
    """Capabilities should expose the authenticated tenant's current product state."""

    app = create_app()
    tenant_context = TenantContext(
        tenant_id=uuid.uuid4(),
        tenant_name="tenant",
        subscription_plan="enterprise",  # type: ignore[arg-type]
        max_execution_tier="critical",  # type: ignore[arg-type]
        api_key_id=uuid.uuid4(),
        api_key_label="test-key",
    )

    async def override_tenant_context():
        return tenant_context

    app.dependency_overrides[get_tenant_context] = override_tenant_context

    with TestClient(app) as client:
        response = client.get("/v1/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["subscription_plan"] == "enterprise"
    assert payload["max_execution_tier"] == "critical"
    assert payload["default_mode"] == "auto"
    assert payload["manual_mode_override_allowed"] is True

    modes = {item["mode"]: item for item in payload["modes"]}
    assert modes["auto"]["enabled"] is True
    assert modes["instant"]["enabled"] is True
    assert modes["thinking"]["enabled"] is False
    assert modes["thinking"]["availability_reason"] == "coming_soon"
    assert modes["verified"]["enabled"] is False
    assert modes["verified"]["availability_reason"] == "coming_soon"

    features = {item["key"]: item for item in payload["features"]}
    assert features["document_upload"]["enabled"] is True
    assert features["workspaces"]["enabled"] is True
    assert features["datasets"]["enabled"] is True
    assert features["agents"]["enabled"] is True
    assert features["agent_chat"]["enabled"] is True
    assert features["conversations"]["enabled"] is True
    assert features["run_history"]["enabled"] is True
    assert features["dashboard"]["enabled"] is True
    assert features["api_key_management"]["enabled"] is True
