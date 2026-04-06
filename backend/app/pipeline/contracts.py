"""Pipeline contracts shared across ingestion and retrieval stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


ChunkingStrategy = Literal[
    "deterministic_token_window_v1",
    "structure_aware_v1",
]


@dataclass(frozen=True)
class ChunkingConfig:
    """Chunking settings for ingestion manifests."""

    max_tokens: int
    overlap_tokens: int
    strategy: ChunkingStrategy = "deterministic_token_window_v1"


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
    section_title: str | None = None
    section_slug: str | None = None
    chunk_role: str = "body"
    starts_with_heading: bool = False
    is_list_block: bool = False

    def to_payload(self) -> dict[str, int | str | bool | None]:
        """Return a JSON-serializable representation of the chunk."""

        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count,
            "character_count": self.character_count,
            "start_token": self.start_token,
            "end_token": self.end_token,
            "section_title": self.section_title,
            "section_slug": self.section_slug,
            "chunk_role": self.chunk_role,
            "starts_with_heading": self.starts_with_heading,
            "is_list_block": self.is_list_block,
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
            section_title=(
                str(payload["section_title"])
                if payload.get("section_title") is not None
                else None
            ),
            section_slug=(
                str(payload["section_slug"])
                if payload.get("section_slug") is not None
                else None
            ),
            chunk_role=str(payload.get("chunk_role", "body")),
            starts_with_heading=bool(payload.get("starts_with_heading", False)),
            is_list_block=bool(payload.get("is_list_block", False)),
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
    section_title: str | None = None
    section_slug: str | None = None
    chunk_role: str = "body"
    starts_with_heading: bool = False
    is_list_block: bool = False


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
    section_title: str | None = None
    section_slug: str | None = None
    chunk_role: str = "body"
    starts_with_heading: bool = False
    is_list_block: bool = False


@dataclass(frozen=True)
class EvidenceItem:
    """Selected evidence chunk prepared for grounding and citation."""

    citation_id: str
    chunk_id: str
    tenant_id: UUID
    namespace_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    score: float
    sources: tuple[str, ...]
    section_title: str | None = None
    section_slug: str | None = None
    chunk_role: str = "body"
    starts_with_heading: bool = False
    is_list_block: bool = False


@dataclass(frozen=True)
class EvidencePackage:
    """Normalized evidence set ready for generation and tracing."""

    retrieved_chunk_ids: list[str]
    selected_evidence_ids: list[str]
    items: list[EvidenceItem]

    def to_prompt_context(self) -> str:
        """Render the evidence package into a stable prompt context block."""

        sections: list[str] = []
        for item in self.items:
            sections.append(
                "\n".join(
                    [
                        f"[{item.citation_id}] chunk_id={item.chunk_id}",
                        f"document_id={item.document_id}",
                        f"chunk_index={item.chunk_index}",
                        f"sources={','.join(item.sources)}",
                        (
                            f"section_title={item.section_title}"
                            if item.section_title
                            else "section_title="
                        ),
                        f"chunk_role={item.chunk_role}",
                        f"starts_with_heading={str(item.starts_with_heading).lower()}",
                        f"is_list_block={str(item.is_list_block).lower()}",
                        item.text,
                    ]
                )
            )
        return "\n\n".join(sections)


@dataclass(frozen=True)
class GroundedAnswerDraft:
    """Grounded answer draft produced before final response shaping."""

    answer_text: str
    cited_evidence_ids: list[str]
    citation_snippets: dict[str, str]
    generator_provider: str
    support_coverage: float = 0.0
    source_diversity: int = 0
