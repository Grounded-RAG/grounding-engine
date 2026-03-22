"""Pipeline contracts shared across ingestion and retrieval stages."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChunkingConfig:
    """Deterministic token-window chunking settings."""

    max_tokens: int
    overlap_tokens: int


@dataclass(frozen=True)
class DocumentChunk:
    """Single deterministic text chunk with provenance metadata."""

    chunk_id: str
    chunk_index: int
    text: str
    token_count: int
    character_count: int
    start_token: int
    end_token: int

    def to_payload(self) -> dict[str, int | str]:
        """Return a JSON-serializable representation of the chunk."""

        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count,
            "character_count": self.character_count,
            "start_token": self.start_token,
            "end_token": self.end_token,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "DocumentChunk":
        """Build a document chunk from a persisted manifest payload."""

        return cls(
            chunk_id=str(payload["chunk_id"]),
            chunk_index=int(payload["chunk_index"]),
            text=str(payload["text"]),
            token_count=int(payload["token_count"]),
            character_count=int(payload["character_count"]),
            start_token=int(payload["start_token"]),
            end_token=int(payload["end_token"]),
        )


@dataclass(frozen=True)
class ChunkManifest:
    """Chunk manifest persisted between extraction and indexing stages."""

    document_id: UUID
    source_artifact_key: str
    chunking_strategy: str
    chunks: list[DocumentChunk]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable manifest payload."""

        return {
            "document_id": str(self.document_id),
            "source_artifact_key": self.source_artifact_key,
            "chunking_strategy": self.chunking_strategy,
            "chunks": [chunk.to_payload() for chunk in self.chunks],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "ChunkManifest":
        """Build a chunk manifest from its stored JSON representation."""

        chunks_payload = payload.get("chunks", [])
        if not isinstance(chunks_payload, list):
            raise ValueError("Chunk manifest payload must contain a chunk list.")

        return cls(
            document_id=UUID(str(payload["document_id"])),
            source_artifact_key=str(payload["source_artifact_key"]),
            chunking_strategy=str(payload["chunking_strategy"]),
            chunks=[
                DocumentChunk.from_payload(chunk_payload)
                for chunk_payload in chunks_payload
                if isinstance(chunk_payload, dict)
            ],
        )


@dataclass(frozen=True)
class RetrievedChunk:
    """Single sparse or dense retrieval hit."""

    chunk_id: str
    tenant_id: UUID
    namespace_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    score: float
    rank: int
    source: str


@dataclass(frozen=True)
class FusedRetrievedChunk:
    """Merged retrieval hit ranked by reciprocal rank fusion."""

    chunk_id: str
    tenant_id: UUID
    namespace_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    fused_score: float
    sources: tuple[str, ...]
