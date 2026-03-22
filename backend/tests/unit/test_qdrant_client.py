"""Unit tests for Qdrant client helpers."""

from __future__ import annotations

from app.core.qdrant_client import ensure_qdrant_collection, upsert_dense_points


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
