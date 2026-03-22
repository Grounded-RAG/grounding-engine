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
