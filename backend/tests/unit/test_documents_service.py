"""Unit tests for document service helpers beyond upload flows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.api.deps import TenantContext
from app.models import DocumentStatus, ExecutionTier, IngestionJobStatus
from app.services.documents import reindex_document_for_tenant


@dataclass
class _FakeScalarResult:
    value: object | None

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def first(self):
        return self.value


class _FakeAsyncSession:
    def __init__(self, responses: list[object | None]) -> None:
        self._responses = list(responses)
        self.added: list[object] = []
        self.committed = False
        self.refreshed: list[object] = []

    async def execute(self, statement, params=None):
        del statement, params
        value = self._responses.pop(0) if self._responses else None
        return _FakeScalarResult(value)

    def add(self, value) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.committed = False

    async def refresh(self, value) -> None:
        self.refreshed.append(value)


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid.uuid4(),
        tenant_name="tenant",
        subscription_plan="pro",  # type: ignore[arg-type]
        max_execution_tier=ExecutionTier.ENTERPRISE,
        api_key_id=uuid.uuid4(),
        api_key_label="test-key",
    )


def _document(*, tenant_id: uuid.UUID, namespace_id: uuid.UUID) -> object:
    return type(
        "DocumentStub",
        (),
        {
            "doc_id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "namespace_id": namespace_id,
            "status": DocumentStatus.INDEXED,
        },
    )()


def _namespace(*, tenant_id: uuid.UUID, namespace_id: uuid.UUID) -> object:
    return type(
        "NamespaceStub",
        (),
        {
            "tenant_id": tenant_id,
            "namespace_id": namespace_id,
        },
    )()


def _job(*, tenant_id: uuid.UUID, document_id: uuid.UUID, status: IngestionJobStatus) -> object:
    return type(
        "JobStub",
        (),
        {
            "job_id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "doc_id": document_id,
            "status": status,
        },
    )()


@pytest.mark.asyncio()
async def test_reindex_document_for_tenant_creates_new_job_when_latest_is_finished() -> None:
    """Reindexing should create a fresh queued job for an already-indexed document."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    document = _document(tenant_id=tenant_context.tenant_id, namespace_id=namespace_id)
    latest_job = _job(
        tenant_id=tenant_context.tenant_id,
        document_id=document.doc_id,
        status=IngestionJobStatus.INDEXED,
    )
    session = _FakeAsyncSession(
        [
            document,
            _namespace(tenant_id=tenant_context.tenant_id, namespace_id=namespace_id),
            latest_job,
        ]
    )

    result = await reindex_document_for_tenant(
        session=session,
        tenant_context=tenant_context,
        document_id=document.doc_id,
    )

    assert result.document is document
    assert result.should_schedule_ingestion is True
    assert result.ingestion_job.doc_id == document.doc_id
    assert result.ingestion_job.status is IngestionJobStatus.QUEUED
    assert document.status is DocumentStatus.UPLOADED
    assert session.committed is True
    assert len(session.added) == 1


@pytest.mark.asyncio()
async def test_reindex_document_for_tenant_reuses_queued_job() -> None:
    """Reindexing should not create duplicate queued/running jobs."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    document = _document(tenant_id=tenant_context.tenant_id, namespace_id=namespace_id)
    latest_job = _job(
        tenant_id=tenant_context.tenant_id,
        document_id=document.doc_id,
        status=IngestionJobStatus.QUEUED,
    )
    session = _FakeAsyncSession(
        [
            document,
            _namespace(tenant_id=tenant_context.tenant_id, namespace_id=namespace_id),
            latest_job,
        ]
    )

    result = await reindex_document_for_tenant(
        session=session,
        tenant_context=tenant_context,
        document_id=document.doc_id,
    )

    assert result.ingestion_job is latest_job
    assert result.should_schedule_ingestion is False
    assert session.added == []
