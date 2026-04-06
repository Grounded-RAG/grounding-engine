"""Unit tests for evidence packaging helpers."""

from __future__ import annotations

import uuid

from app.pipeline.contracts import FusedRetrievedChunk, RetrievedChunk
from app.services.evidence import package_evidence
from app.services.retrieval import RetrievalBundle


def _fused_hit(*, chunk_id: str, chunk_index: int, score: float) -> FusedRetrievedChunk:
    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    return FusedRetrievedChunk(
        chunk_id=chunk_id,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        chunk_index=chunk_index,
        text=f"text for {chunk_id}",
        fused_score=score,
        sources=("dense", "sparse"),
    )


def _retrieved_hit(*, chunk_id: str, source: str, rank: int) -> RetrievedChunk:
    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    return RetrievedChunk(
        chunk_id=chunk_id,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        chunk_index=rank - 1,
        text=f"text for {chunk_id}",
        score=1.0 / rank,
        rank=rank,
        source=source,
    )


def test_package_evidence_selects_top_fused_hits() -> None:
    """Evidence packaging should select the highest-ranked fused hits first."""

    bundle = RetrievalBundle(
        sparse_hits=[
            _retrieved_hit(chunk_id="chunk-1", source="sparse", rank=1),
            _retrieved_hit(chunk_id="chunk-2", source="sparse", rank=2),
        ],
        dense_hits=[
            _retrieved_hit(chunk_id="chunk-2", source="dense", rank=1),
            _retrieved_hit(chunk_id="chunk-3", source="dense", rank=2),
        ],
        fused_hits=[
            _fused_hit(chunk_id="chunk-2", chunk_index=1, score=0.9),
            _fused_hit(chunk_id="chunk-1", chunk_index=0, score=0.8),
            _fused_hit(chunk_id="chunk-3", chunk_index=2, score=0.6),
        ],
    )

    package = package_evidence(bundle, limit=2)

    assert package.retrieved_chunk_ids == ["chunk-2", "chunk-1", "chunk-3"]
    assert package.selected_evidence_ids == ["chunk-2", "chunk-1"]
    assert [item.citation_id for item in package.items] == ["E001", "E002"]
    assert [item.chunk_id for item in package.items] == ["chunk-2", "chunk-1"]


def test_package_evidence_reranks_hits_by_query_answerability() -> None:
    """Query-aware packaging should prefer chunks that can directly answer the question."""

    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="chunk-experience",
                tenant_id=uuid.uuid4(),
                namespace_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_index=2,
                text="Professional experience: AI Engineer at iCog Labs.",
                fused_score=0.92,
                sources=("dense", "sparse"),
            ),
            FusedRetrievedChunk(
                chunk_id="chunk-name",
                tenant_id=uuid.uuid4(),
                namespace_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_index=0,
                text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
                fused_score=0.83,
                sources=("dense",),
            ),
        ],
    )

    package = package_evidence(
        bundle,
        query_text="What is the name of the resume owner?",
        limit=1,
    )

    assert package.selected_evidence_ids == ["chunk-name"]


def test_package_evidence_keeps_single_best_hit_for_field_query_even_with_larger_limit() -> None:
    """Focused field extraction should stay pure instead of packaging multiple distractor chunks."""

    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="chunk-name",
                tenant_id=uuid.uuid4(),
                namespace_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_index=0,
                text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
                fused_score=0.82,
                sources=("dense", "sparse"),
            ),
            FusedRetrievedChunk(
                chunk_id="chunk-experience",
                tenant_id=uuid.uuid4(),
                namespace_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_index=2,
                text="PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs.",
                fused_score=0.91,
                sources=("dense",),
            ),
        ],
    )

    package = package_evidence(
        bundle,
        query_text="What is the name of the person?",
        limit=3,
    )

    assert package.selected_evidence_ids == ["chunk-name"]


def test_package_evidence_renders_stable_prompt_context() -> None:
    """Evidence packages should render a stable prompt context for generation."""

    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            _fused_hit(chunk_id="chunk-9", chunk_index=3, score=0.75),
        ],
    )

    package = package_evidence(bundle, limit=1)
    context = package.to_prompt_context()

    assert "[E001] chunk_id=chunk-9" in context
    assert "chunk_index=3" in context
    assert "sources=dense,sparse" in context
    assert "text for chunk-9" in context


def test_package_evidence_handles_empty_retrieval_bundle() -> None:
    """Empty retrieval bundles should yield an empty evidence package."""

    package = package_evidence(
        RetrievalBundle(sparse_hits=[], dense_hits=[], fused_hits=[]),
        limit=3,
    )

    assert package.retrieved_chunk_ids == []
    assert package.selected_evidence_ids == []
    assert package.items == []
    assert package.to_prompt_context() == ""


def test_package_evidence_prefers_diverse_chunks_for_dataset_summary() -> None:
    """Dataset summaries should keep complementary chunks instead of adjacent near-duplicates."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="doc-a-header",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=doc_a,
                chunk_index=0,
                text="Dataset A overview and introduction.",
                fused_score=0.95,
                sources=("dense", "sparse"),
            ),
            FusedRetrievedChunk(
                chunk_id="doc-a-next",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=doc_a,
                chunk_index=1,
                text="Dataset A second chunk with similar overview wording.",
                fused_score=0.92,
                sources=("dense",),
            ),
            FusedRetrievedChunk(
                chunk_id="doc-b-header",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=doc_b,
                chunk_index=0,
                text="Dataset B introduction with skills and experience sections.",
                fused_score=0.81,
                sources=("sparse",),
            ),
        ],
    )

    package = package_evidence(
        bundle,
        query_text="What is the dataset about?",
        limit=2,
    )

    assert package.selected_evidence_ids == ["doc-a-header", "doc-b-header"]


def test_package_evidence_keeps_complementary_list_chunks() -> None:
    """List-style questions may keep adjacent chunks when they add complementary categories."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    other_document_id = uuid.uuid4()
    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="skills-primary",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=3,
                text="TECHNICAL SKILLS\nProgramming Languages: Python, Go, TypeScript",
                fused_score=0.94,
                sources=("dense", "sparse"),
            ),
            FusedRetrievedChunk(
                chunk_id="skills-adjacent",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=4,
                text="TECHNICAL SKILLS\nFrameworks: FastAPI, React, Next.js",
                fused_score=0.93,
                sources=("dense",),
            ),
            FusedRetrievedChunk(
                chunk_id="skills-other-doc",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=other_document_id,
                chunk_index=1,
                text="TOOLS\nDocker, GitHub, Elasticsearch",
                fused_score=0.79,
                sources=("sparse",),
            ),
        ],
    )

    package = package_evidence(
        bundle,
        query_text="What are the technical skills?",
        limit=2,
    )

    assert package.selected_evidence_ids == ["skills-primary", "skills-adjacent"]


def test_package_evidence_filters_incidental_collection_mentions_when_section_exists() -> None:
    """Collection questions should prefer real sections over incidental sentence-level mentions."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    bundle = RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="awards-narrative",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=6,
                text="Enhanced skills in advanced ICT and Artificial intelligence through targeted workshops.",
                fused_score=0.98,
                sources=("dense", "sparse"),
            ),
            FusedRetrievedChunk(
                chunk_id="skills-section",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=8,
                text=(
                    "TECHNICAL SKILLS\n"
                    "Programming Languages: Python, Go, TypeScript\n"
                    "Frameworks: FastAPI, React, Next.js"
                ),
                fused_score=0.85,
                sources=("dense",),
            ),
        ],
    )

    package = package_evidence(
        bundle,
        query_text="What is her skill?",
        limit=2,
    )

    assert package.selected_evidence_ids == ["skills-section"]
