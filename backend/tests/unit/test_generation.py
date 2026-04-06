"""Unit tests for grounded generation helpers."""

from __future__ import annotations

import uuid

import pytest

from app.core.llm_client import GroundedGenerationError, generate_grounded_draft
from app.core.gemini_generator import GeminiGenerationError
from app.core.openai_generator import OpenAICompatibleGenerationError
from app.pipeline.contracts import EvidenceItem, EvidencePackage
from app.services.generation import GenerationBackend, generate_answer_from_evidence


def _evidence_item(*, citation_id: str, chunk_id: str, text: str) -> EvidenceItem:
    return EvidenceItem(
        citation_id=citation_id,
        chunk_id=chunk_id,
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        text=text,
        score=0.9,
        sources=("dense", "sparse"),
    )


def test_generate_grounded_draft_uses_evidence_only() -> None:
    """Grounded generation should compose its answer from packaged evidence."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded handles tenant-safe uploads. It stores files in object storage.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-2",
                text="Ingestion jobs track processing status for each document.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="How does grounded handle uploads and processing?",
        evidence_package=evidence_package,
    )

    assert "Grounded handles tenant-safe uploads." in draft.answer_text
    assert "Ingestion jobs track processing status for each document." in draft.answer_text
    assert "[E001]" in draft.answer_text
    assert "[E002]" in draft.answer_text
    assert draft.cited_evidence_ids == ["chunk-1", "chunk-2"]
    assert draft.citation_snippets["chunk-1"] == "Grounded handles tenant-safe uploads."
    assert draft.generator_provider == "local-grounded-v1"
    assert draft.support_coverage == 1.0
    assert draft.source_diversity == 2


def test_generate_grounded_draft_prefers_query_aligned_sentence() -> None:
    """Grounded generation should prefer the sentence most aligned with the query."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text=(
                    "This system has many components. "
                    "Hybrid retrieval merges sparse and dense search results. "
                    "The project also supports tenant isolation."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="Explain hybrid retrieval",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith(
        "Hybrid retrieval merges sparse and dense search results. [E001]"
    )
    assert draft.citation_snippets["chunk-1"] == "Hybrid retrieval merges sparse and dense search results."


def test_generate_grounded_draft_synthesizes_dataset_summary_from_structure() -> None:
    """Dataset summaries should synthesize a high-level overview instead of echoing a fragment."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-header", "chunk-sections"],
        selected_evidence_ids=["chunk-header", "chunk-sections"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-header",
                text=(
                    "Samrawit Gebremaryam Bahta\n"
                    "samrawitgebremaryam121@gmail.com\n"
                    "EDUCATION\nBSc in Software Engineering"
                ),
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-sections",
                text=(
                    "PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs\n"
                    "TECHNICAL SKILLS\nPython, Go, TypeScript\n"
                    "AWARDS\nHuawei Seeds for the Future"
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What is this dataset about?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The dataset contains")
    assert "Samrawit Gebremaryam Bahta" in draft.answer_text
    assert "professional experience" in draft.answer_text.lower()
    assert "[E001]" in draft.answer_text


def test_generate_grounded_draft_rejects_empty_evidence() -> None:
    """Grounded generation should fail cleanly without evidence."""

    with pytest.raises(GroundedGenerationError):
        generate_grounded_draft(
            query_text="What happened?",
            evidence_package=EvidencePackage(
                retrieved_chunk_ids=[],
                selected_evidence_ids=[],
                items=[],
            ),
        )


def test_generate_grounded_draft_rejects_non_meaningful_greeting_queries() -> None:
    """Short greetings should degrade instead of reusing unrelated evidence."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Samrawit studies software engineering at Addis Ababa Science and Technology University.",
            ),
        ],
    )

    with pytest.raises(GroundedGenerationError, match="meaningful query terms"):
        generate_grounded_draft(
            query_text="hi",
            evidence_package=evidence_package,
        )


def test_generate_grounded_draft_omits_irrelevant_evidence_items() -> None:
    """Only evidence that actually supports the query should be cited."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Education: BSc in Software Engineering at Addis Ababa Science and Technology University.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-2",
                text="Awarded for a Huawei Seeds for the Future project in China.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What is her education status?",
        evidence_package=evidence_package,
    )

    assert draft.cited_evidence_ids == ["chunk-1"]
    assert "[E002]" not in draft.answer_text


def test_generate_grounded_draft_can_extract_name_like_answer() -> None:
    """Field-style questions should prefer exact answer lines over unrelated descriptive bullets."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-name", "chunk-experience"],
        selected_evidence_ids=["chunk-name", "chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-name",
                text="Samrawit Gebremaryam Bahta\nsamrawitgebremaryam121@gmail.com\n+251-989-985-456",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-experience",
                text="Professional experience: AI Engineer at iCog Labs building grounded retrieval systems.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What is the name of the resume owner?",
        evidence_package=evidence_package,
    )

    assert draft.cited_evidence_ids[0] == "chunk-name"
    assert draft.answer_text.startswith("The person's name is Samrawit Gebremaryam Bahta")
    assert "[E001]" in draft.answer_text
    assert "[E002]" not in draft.answer_text


def test_generate_grounded_draft_prefers_skills_section_over_incidental_skill_wording() -> None:
    """Skills questions should prefer actual skill sections over unrelated mentions of skills."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-awards", "chunk-skills"],
        selected_evidence_ids=["chunk-awards", "chunk-skills"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-awards",
                text="Enhanced skills in advanced ICT and Artificial intelligence through targeted workshops.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-skills",
                text=(
                    "TECHNICAL SKILLS\n"
                    "AI & Machine Learning: PyTorch, Scikit-learn, Hugging Face, RAG\n"
                    "Programming Languages: Python, Go, TypeScript"
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What are her technical skills?",
        evidence_package=evidence_package,
    )

    assert draft.cited_evidence_ids[0] == "chunk-skills"
    assert draft.answer_text.startswith("The listed technical skills are")
    assert "PyTorch" in draft.answer_text
    assert "[E002]" in draft.answer_text
    assert "[E001]" not in draft.answer_text


def test_generate_grounded_draft_rejects_definition_queries_without_definition_support() -> None:
    """Mentioning a term should not count as defining it."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-course", "chunk-skills"],
        selected_evidence_ids=["chunk-course", "chunk-skills"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-course",
                text="Relevant courses include Introduction to Machine Learning and Advanced Programming.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-skills",
                text="AI & Machine Learning: PyTorch, Scikit-learn, Hugging Face.",
            ),
        ],
    )

    with pytest.raises(GroundedGenerationError, match="query-aligned support"):
        generate_grounded_draft(
            query_text="What does machine learning mean?",
            evidence_package=evidence_package,
        )


def test_generate_grounded_draft_does_not_misclassify_experience_query_as_name() -> None:
    """Queries mentioning a person should still answer the requested field, not default to name."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-name", "chunk-experience"],
        selected_evidence_ids=["chunk-name", "chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-name",
                text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-experience",
                text="PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs working on grounded retrieval systems.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What is the work experience of the person?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The work experience is")
    assert "AI Engineer at iCog Labs" in draft.answer_text
    assert "The person's name is" not in draft.answer_text
    assert draft.cited_evidence_ids == ["chunk-experience"]


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_delegates_to_generation_backend(monkeypatch) -> None:
    """The generation service should delegate to the grounded generator backend."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded returns answers anchored in retrieved evidence.",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="local_grounded_v1",
            implementation="local",
        ),
    )

    draft = await generate_answer_from_evidence(
        query_text="What does grounded return?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == (
        "Grounded returns answers anchored in retrieved evidence. [E001]"
    )
    assert draft.generator_provider == "local-grounded-v1"
    assert draft.support_coverage == 1.0


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_falls_back_from_openai_backend(monkeypatch) -> None:
    """Provider-backed generation should fall back cleanly when the provider fails."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded returns answers anchored in retrieved evidence.",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="openai_compatible_v1",
            implementation="openai_compatible",
        ),
    )

    async def fake_generate_openai_compatible_draft(**kwargs):
        del kwargs
        raise OpenAICompatibleGenerationError("provider unavailable")

    monkeypatch.setattr(
        "app.services.generation.generate_openai_compatible_draft",
        fake_generate_openai_compatible_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="What does grounded return?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == (
        "Grounded returns answers anchored in retrieved evidence. [E001]"
    )
    assert draft.generator_provider == "local-grounded-v1:fallback_from_openai_compatible_v1"


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_falls_back_from_gemini_backend(monkeypatch) -> None:
    """Gemini-backed generation should also fall back cleanly when unavailable."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded returns answers anchored in retrieved evidence.",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="gemini_v1",
            implementation="gemini",
        ),
    )

    async def fake_generate_gemini_draft(**kwargs):
        del kwargs
        raise GeminiGenerationError("provider unavailable")

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="What does grounded return?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == (
        "Grounded returns answers anchored in retrieved evidence. [E001]"
    )
    assert draft.generator_provider == "local-grounded-v1:fallback_from_gemini_v1"


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_rejects_weak_provider_field_answer(monkeypatch) -> None:
    """Provider answers that cite irrelevant field evidence should fall back to deterministic grounding."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-name", "chunk-experience"],
        selected_evidence_ids=["chunk-name", "chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-name",
                text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-experience",
                text="PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs working on grounded retrieval systems.",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="gemini_v1",
            implementation="gemini",
        ),
    )

    async def fake_generate_gemini_draft(**kwargs):
        del kwargs
        from app.pipeline.contracts import GroundedAnswerDraft

        return GroundedAnswerDraft(
            answer_text="Samrawit Gebremaryam Bahta [E001] PROFESSIONAL EXPERIENCE [E002]",
            cited_evidence_ids=["chunk-name", "chunk-experience"],
            citation_snippets={
                "chunk-name": "Samrawit Gebremaryam Bahta",
                "chunk-experience": "PROFESSIONAL EXPERIENCE",
            },
            generator_provider="gemini:gemini-2.5-flash",
            support_coverage=1.0,
            source_diversity=2,
        )

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="What is the name of the person?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The person's name is Samrawit Gebremaryam Bahta")
    assert draft.generator_provider == "local-grounded-v1:fallback_from_gemini_v1"


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_rejects_weak_provider_summary_answer(monkeypatch) -> None:
    """Fragmentary provider summaries should fall back to deterministic summary synthesis."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-header", "chunk-sections"],
        selected_evidence_ids=["chunk-header", "chunk-sections"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-header",
                text=(
                    "Samrawit Gebremaryam Bahta\n"
                    "EDUCATION\nBSc in Software Engineering"
                ),
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-sections",
                text=(
                    "PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs\n"
                    "TECHNICAL SKILLS\nPython, Go, TypeScript"
                ),
            ),
        ],
    )

    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="gemini_v1",
            implementation="gemini",
        ),
    )

    async def fake_generate_gemini_draft(**kwargs):
        del kwargs
        from app.pipeline.contracts import GroundedAnswerDraft

        return GroundedAnswerDraft(
            answer_text="across heterogeneous datasets. [E001]",
            cited_evidence_ids=["chunk-header"],
            citation_snippets={
                "chunk-header": "across heterogeneous datasets.",
            },
            generator_provider="gemini:gemini-2.5-flash",
            support_coverage=0.5,
            source_diversity=1,
        )

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="What is this dataset about?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The dataset contains")
    assert draft.generator_provider == "local-grounded-v1:fallback_from_gemini_v1"
