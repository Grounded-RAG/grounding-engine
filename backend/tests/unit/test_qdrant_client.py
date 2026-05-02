"""Unit tests for Qdrant client helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.core.qdrant_client import (
    delete_dense_points_for_document,
    get_qdrant_client,
    ensure_qdrant_collection,
    reset_qdrant_client,
    search_dense_points,
    upsert_dense_points,
)


class FakeQdrantClient:
    """Minimal fake Qdrant client for collection and upsert tests."""

    def __init__(self) -> None:
        self.created_collections: list[tuple[str, object]] = []
        self.upserts: list[tuple[str, list[object], bool]] = []
        self.exists = False

    def collection_exists(self, *, collection_name: str) -> bool:
        assert collection_name == "grounded_chunks"
        return self.exists

    def create_collection(self, *, collection_name: str, vectors_config: object) -> None:
        self.created_collections.append((collection_name, vectors_config))
        self.exists = True

    def upsert(self, *, collection_name: str, points: list[object], wait: bool) -> None:
        self.upserts.append((collection_name, points, wait))

    def delete(self, *, collection_name: str, points_selector: object, wait: bool) -> None:
        self.deletes.append((collection_name, points_selector, wait))

    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        query_filter: object,
        limit: int,
        with_payload: bool,
        with_vectors: bool,
    ) -> object:
        self.searches.append(
            (
                collection_name,
                query,
                query_filter,
                limit,
                with_payload,
                with_vectors,
            )
        )
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    score=0.9,
                    payload={
                        "chunk_id": "chunk-1",
                        "tenant_id": str(uuid.uuid4()),
                        "namespace_id": str(uuid.uuid4()),
                        "document_id": str(uuid.uuid4()),
                        "chunk_index": 0,
                        "text": "alpha beta",
                    },
                )
            ]
        )


def test_ensure_qdrant_collection_creates_missing_collection(monkeypatch) -> None:
    """Qdrant helper should create the configured collection when missing."""

    client = FakeQdrantClient()
    monkeypatch.setattr("app.core.qdrant_client.get_qdrant_client", lambda: client)

    ensure_qdrant_collection(vector_size=16)

    assert len(client.created_collections) == 1
    assert client.created_collections[0][0] == "grounded_chunks"


def test_upsert_dense_points_writes_all_points(monkeypatch) -> None:
    """Upsert helper should write all provided points after ensuring the collection."""

    client = FakeQdrantClient()
    client.exists = True
    monkeypatch.setattr("app.core.qdrant_client.get_qdrant_client", lambda: client)

    points = ["point-1", "point-2"]
    written = upsert_dense_points(points=points, vector_size=16)

    assert written == 2
    assert client.upserts == [("grounded_chunks", points, True)]


def test_search_dense_points_applies_tenant_namespace_filter(monkeypatch) -> None:
    """Dense search helper should scope queries by tenant and namespace."""

    client = FakeQdrantClient()
    client.exists = True
    client.searches = []
    monkeypatch.setattr("app.core.qdrant_client.get_qdrant_client", lambda: client)

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    results = search_dense_points(
        query_vector=[0.1, 0.2],
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        limit=5,
    )

    assert len(results) == 1
    assert len(client.searches) == 1
    collection_name, query_vector, query_filter, limit, with_payload, with_vectors = (
        client.searches[0]
    )
    assert collection_name == "grounded_chunks"
    assert query_vector == [0.1, 0.2]
    assert limit == 5
    assert with_payload is True
    assert with_vectors is False
    must_conditions = query_filter.must
    assert len(must_conditions) == 2
    assert must_conditions[0].key == "tenant_id"
    assert must_conditions[0].match.value == str(tenant_id)
    assert must_conditions[1].key == "namespace_id"
    assert must_conditions[1].match.value == str(namespace_id)


def test_delete_dense_points_for_document_applies_tenant_document_filter(monkeypatch) -> None:
    """Dense deletion should scope cleanup to one tenant-scoped document."""

    client = FakeQdrantClient()
    client.exists = True
    client.deletes = []
    monkeypatch.setattr("app.core.qdrant_client.get_qdrant_client", lambda: client)

    tenant_id = uuid.uuid4()
    document_id = uuid.uuid4()
    delete_dense_points_for_document(
        tenant_id=tenant_id,
        document_id=document_id,
    )

    assert len(client.deletes) == 1
    collection_name, selector, wait = client.deletes[0]
    assert collection_name == "grounded_chunks"
    assert wait is True
    must_conditions = selector.filter.must
    assert len(must_conditions) == 2
    assert must_conditions[0].key == "tenant_id"
    assert must_conditions[0].match.value == str(tenant_id)
    assert must_conditions[1].key == "document_id"
    assert must_conditions[1].match.value == str(document_id)


def test_get_qdrant_client_respects_compatibility_flag(monkeypatch) -> None:
    """Qdrant client construction should use the configured compatibility policy."""

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, url: str, check_compatibility: bool) -> None:
            captured["url"] = url
            captured["check_compatibility"] = check_compatibility

    monkeypatch.setenv("QDRANT_CHECK_COMPATIBILITY", "false")
    monkeypatch.setattr("app.core.qdrant_client.QdrantClient", FakeClient)

    from app.config import get_settings

    get_settings.cache_clear()
    reset_qdrant_client()
    try:
        client = get_qdrant_client()
    finally:
        reset_qdrant_client()
        get_settings.cache_clear()

    assert isinstance(client, FakeClient)
    assert captured["url"] == "http://localhost:6333/"
    assert captured["check_compatibility"] is False
