"""Repository protocol definitions for the data-access layer.

Each protocol describes the minimum interface a storage backend must satisfy.
Concrete implementations live alongside the models they manage; these protocols
exist so services can depend on abstractions rather than concrete SQLAlchemy calls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class DocumentRepository(Protocol):
    """Minimal interface for document persistence."""

    async def get_by_id(self, document_id: UUID) -> object | None: ...
    async def list_by_namespace(self, namespace_id: UUID, *, limit: int, offset: int) -> list[object]: ...
    async def create(self, payload: dict[str, object]) -> object: ...
    async def delete(self, document_id: UUID) -> bool: ...


@runtime_checkable
class NamespaceRepository(Protocol):
    """Minimal interface for namespace persistence."""

    async def get_by_id(self, namespace_id: UUID) -> object | None: ...
    async def list_by_tenant(self, tenant_id: UUID) -> list[object]: ...
    async def create(self, payload: dict[str, object]) -> object: ...
    async def update(self, namespace_id: UUID, payload: dict[str, object]) -> object | None: ...


@runtime_checkable
class QueryTraceRepository(Protocol):
    """Minimal interface for query trace persistence."""

    async def get_by_id(self, trace_id: UUID) -> object | None: ...
    async def list_by_namespace(self, namespace_id: UUID, *, limit: int) -> list[object]: ...
    async def upsert(self, trace_id: UUID, payload: dict[str, object]) -> object: ...


__all__ = [
    "DocumentRepository",
    "NamespaceRepository",
    "QueryTraceRepository",
]
