"""Route-level tests for the Standard query endpoint."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_db_session, get_tenant_context
from app.main import create_app
from app.schemas.query import GroundedAnswerResponse


def test_query_endpoint_returns_structured_answer_and_trace_header(monkeypatch) -> None:
    """The query endpoint should return the structured answer contract and trace id."""

    app = create_app()
    tenant_context = TenantContext(
        tenant_id=uuid.uuid4(),
        tenant_name="tenant",
        subscription_plan="pro",  # type: ignore[arg-type]
        max_execution_tier="enterprise",  # type: ignore[arg-type]
        api_key_id=uuid.uuid4(),
        api_key_label="test-key",
    )

    async def override_tenant_context():
        return tenant_context

    async def override_db_session():
        yield object()

    app.dependency_overrides[get_tenant_context] = override_tenant_context
    app.dependency_overrides[get_db_session] = override_db_session

    trace_id = uuid.uuid4()

    async def fake_execute_standard_query(*, session, tenant_context, query_request):
        del session, tenant_context
        from app.services.query import QueryExecutionResult

        assert str(query_request.namespace_id)
        return QueryExecutionResult(
            response=GroundedAnswerResponse(
                answer="Grounded supports tenant-safe uploads. [E001]",
                citations=[
                    {
                        "citation_id": "E001",
                        "chunk_id": "chunk-1",
                        "document_id": uuid.uuid4(),
                        "chunk_index": 0,
                        "quote": "Grounded supports tenant-safe uploads.",
                    }
                ],
                confidence_score=0.9,
                verification_status="passed",
                degraded_reasons=[],
            ),
            trace_id=trace_id,
        )

    monkeypatch.setattr(
        "app.api.v1.query.execute_standard_query",
        fake_execute_standard_query,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/query",
            json={
                "namespace_id": str(uuid.uuid4()),
                "query": "How does grounded work?",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == str(trace_id)
    assert response.json()["verification_status"] == "passed"
    assert response.json()["degraded_reasons"] == []
