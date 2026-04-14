"""Unit tests for grounded generation helpers."""

from __future__ import annotations

import uuid

import pytest

from app.core.llm_client import GroundedGenerationError, generate_grounded_draft
from app.core.gemini_generator import (
    GeminiGenerationError,
    _build_prompt,
    _generation_config_for_mode,
    _parse_result,
)
from app.core.openai_generator import OpenAICompatibleGenerationError
from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
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


def test_generate_grounded_draft_renders_action_questions_from_responsibility_lines() -> None:
    """Action questions should summarize concrete responsibilities, not echo a raw section label."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-experience"],
        selected_evidence_ids=["chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-experience",
                text=(
                    "PROFESSIONAL EXPERIENCE\n"
                    "AI Engineer\n"
                    "iCog Labs\n"
                    "Architected and developed emotionally intelligent AI characters.\n"
                    "Integrated SPMiner-inspired neural mining techniques with improved visualization modules."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What did she do at iCog Labs?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("In icog labs, the evidence shows work including")
    assert "Architected and developed emotionally intelligent AI characters" in draft.answer_text
    assert "Integrated SPMiner-inspired neural mining techniques" in draft.answer_text


def test_generate_grounded_draft_renders_comparison_questions_as_boolean_with_evidence() -> None:
    """Comparison questions should answer yes/no using the relevant context rather than dumping a snippet."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-role-1", "chunk-role-2"],
        selected_evidence_ids=["chunk-role-1", "chunk-role-2"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-role-1",
                text="AI Engineer\niCog Labs\nArchitected grounded retrieval systems.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-role-2",
                text="Backend | AI Developer Intern\niCog Labs\nImplemented an Elasticsearch autocomplete system.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="Is her experience only in iCog Labs?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("Yes.")
    assert "icog labs" in draft.answer_text.casefold()


def test_generate_grounded_draft_renders_entity_context_questions_cleanly() -> None:
    """Entity-in-context questions should return a grounded yes/no answer from the matching snippet."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-experience"],
        selected_evidence_ids=["chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-experience",
                text="Integrated SPMiner-inspired neural mining techniques with improved visualization modules.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="Did she work on pattern miner?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("Yes.")
    assert "neural mining techniques" in draft.answer_text


def test_generate_grounded_draft_summarizes_paper_like_dataset_using_title_and_topic() -> None:
    """Paper-like datasets should summarize from titles/topic sentences, not generic section labels."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-paper"],
        selected_evidence_ids=["chunk-paper"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-paper",
                text=(
                    "Explainable AI in Software Engineering\n"
                    "Introduction\n"
                    "This paper examines how explainable AI methods help software teams debug, validate, and govern AI-enabled systems."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What is the dataset about?",
        evidence_package=evidence_package,
    )

    assert "Explainable AI in Software Engineering" in draft.answer_text
    assert "The dataset is about" in draft.answer_text
    assert "This paper examines how explainable AI methods help software teams debug" in draft.answer_text
    assert "The dataset contains Introduction" not in draft.answer_text


def test_generate_grounded_draft_renders_collection_answers_from_prose_sentences() -> None:
    """Collection queries on prose should extract relevant sentences rather than raw paragraphs."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-xai"],
        selected_evidence_ids=["chunk-xai"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-xai",
                text=(
                    "One major challenge is that some explanations create a false sense of trust in incorrect outputs. "
                    "Another emerging challenge concerns generative AI and large language models, where open-ended outputs are harder to explain safely. "
                    "Finally, software teams must integrate explanations into documentation, monitoring, testing, and governance workflows."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What are the challenges for xAI?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The listed challenges are")
    assert "false sense of trust" in draft.answer_text
    assert "generative AI and large language models" in draft.answer_text


def test_generate_grounded_draft_ignores_outline_headings_for_challenge_lists() -> None:
    """Collection answers should ignore numbered section headings and use challenge prose."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-outline", "chunk-challenges", "chunk-summary"],
        selected_evidence_ids=["chunk-outline", "chunk-challenges", "chunk-summary"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-outline",
                text=(
                    "2. New Opportunities in Software Engineering\n"
                    "Overview text.\n"
                    "3. New Challenges in Software Engineering"
                ),
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-challenges",
                text=(
                    "One major challenge is the trade-off between model performance and interpretability. "
                    "Another critical challenge is the evaluation of explanations. "
                    "Scalability is also a concern as models grow larger and more complex."
                ),
            ),
            _evidence_item(
                citation_id="E003",
                chunk_id="chunk-summary",
                text=(
                    "However, challenges such as evaluation, scalability, and balancing accuracy with "
                    "interpretability remain significant."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What are the challenges?",
        evidence_package=evidence_package,
    )

    assert "New Opportunities in Software Engineering" not in draft.answer_text
    assert "New Challenges in Software Engineering" not in draft.answer_text
    assert "trade-off between model performance and interpretability" in draft.answer_text
    assert "evaluation of explanations" in draft.answer_text


def test_generate_grounded_draft_ignores_title_case_section_headings_for_collection_answers() -> None:
    """Title-case section headers should not become the final list items."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-challenges"],
        selected_evidence_ids=["chunk-challenges"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-challenges",
                text=(
                    "New Challenges in Software Engineering\n"
                    "One challenge is that inaccurate explanations can create false trust in high-stakes systems.\n"
                    "Another challenge is that generative AI outputs are open-ended, so engineers need ways to surface uncertainty, hallucination risks, and retrieval gaps.\n"
                    "A further challenge is that teams must integrate explanations into testing, monitoring, documentation, and CI/CD workflows."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What are the challenges?",
        evidence_package=evidence_package,
    )

    assert "New Challenges in Software Engineering" not in draft.answer_text
    assert "false trust in high-stakes systems" in draft.answer_text
    assert "retrieval gaps" in draft.answer_text


def test_generate_grounded_draft_renders_multiple_collection_families_cleanly() -> None:
    """Questions like methods-and-tools should include both item families, not just the header."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-methods-tools"],
        selected_evidence_ids=["chunk-methods-tools"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-methods-tools",
                text=(
                    "Methods, Technologies, and Tools\n"
                    "XAI methods include intrinsic approaches such as decision trees, linear models, and rule-based systems.\n"
                    "Post-hoc methods include LIME, SHAP, and counterfactual explanations.\n"
                    "Common tools include Captum for PyTorch models, InterpretML for glassbox models and visualizations, and Google's What-If Tool for interactive analysis."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What are the methods, the tools?",
        evidence_package=evidence_package,
    )

    assert "The listed methods and tools are" in draft.answer_text
    assert "decision trees" in draft.answer_text
    assert "LIME, SHAP, and counterfactual explanations" in draft.answer_text
    assert "Captum" in draft.answer_text


def test_generate_grounded_draft_answers_mixed_boolean_action_role_question() -> None:
    """Role + where + what-did questions should return a grounded action answer."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-experience"],
        selected_evidence_ids=["chunk-experience"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-experience",
                text=(
                    "PROFESSIONAL EXPERIENCE\n"
                    "AI Engineer\n"
                    "iCog Labs\n"
                    "Architected and developed emotionally intelligent AI characters.\n"
                    "Integrated SPMiner-inspired neural mining techniques with improved visualization modules."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="does she has an experiance as a AI enginner if so where and what did she do there",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("Yes.")
    assert "AI Engineer" in draft.answer_text
    assert "iCog Labs" in draft.answer_text
    assert "Architected and developed emotionally intelligent AI characters" in draft.answer_text


def test_generate_grounded_draft_renders_count_questions_from_structured_items() -> None:
    """Count questions should return a grounded numeric answer when structured item titles are present."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-projects"],
        selected_evidence_ids=["chunk-projects"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-projects",
                text=(
                    "PROJECTS\n"
                    "The Traveler's Pocket Pal - Travel Companion\n"
                    "Developed an AI-powered travel assistant.\n"
                    "StyleCraft - Personalized AI Writing Assistant\n"
                    "Built a RAG-based writing system."
                ),
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="How many projects does she have?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text.startswith("The evidence shows 2 projects:")
    assert "Traveler's Pocket Pal" in draft.answer_text
    assert "StyleCraft" in draft.answer_text


def test_generate_grounded_draft_extracts_explicit_count_from_prose_sentence() -> None:
    """Count questions should return a direct numeric phrase when prose states the answer explicitly."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-fleet"],
        selected_evidence_ids=["chunk-fleet"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-fleet",
                text="Fleet Details\nThe city purchased 12 electric vans from Voltara Mobility for the pilot.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="How many electric vans were purchased?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "12 electric vans [E001]"


def test_generate_grounded_draft_extracts_exact_supplier_name_from_prose_sentence() -> None:
    """Supplier/company lookups should return the organization, not the whole paragraph."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-fleet"],
        selected_evidence_ids=["chunk-fleet"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-fleet",
                text="Fleet Details\nThe city purchased 12 electric vans from Voltara Mobility for the pilot.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="Which company supplied the vans?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "The company is Voltara Mobility [E001]"


def test_generate_grounded_draft_computes_numeric_difference_for_comparison_question() -> None:
    """Difference questions should compute the grounded arithmetic result instead of paraphrasing both sentences."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-old-cost", "chunk-new-cost"],
        selected_evidence_ids=["chunk-old-cost", "chunk-new-cost"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-old-cost",
                text="Costs and Savings\nBefore the pilot, the city spent about $18,400 on fuel over six months.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-new-cost",
                text="Costs and Savings\nDuring the pilot, electricity costs totaled $6,900 over six months.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="What was the difference between old fuel cost and new electricity cost over six months?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "The difference is $11,500 [E001] [E002]."


def test_generate_grounded_draft_answers_start_and_end_date_range_cleanly() -> None:
    """Start/end date questions should synthesize a grounded range instead of dropping one endpoint."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-start", "chunk-end"],
        selected_evidence_ids=["chunk-start", "chunk-end"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-start",
                text="Pilot Overview\nIn January 2025, the city of Lydon launched the electric van pilot.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-end",
                text="Pilot Overview\nThe pilot lasted for six months and ended in June 2025.",
            ),
        ],
    )

    draft = generate_grounded_draft(
        query_text="When did the pilot start and end?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "It started in January 2025 [E001] and ended in June 2025 [E002]."


def test_parse_gemini_result_accepts_array_citation_snippets() -> None:
    """Gemini JSON parsing should accept schema-friendly citation snippet arrays."""

    parsed = _parse_result(
        {
            "answer_text": "Grounded uses hybrid retrieval.",
            "cited_evidence_ids": ["chunk-1"],
            "citation_snippets": [
                {"chunk_id": "chunk-1", "snippet": "Grounded uses hybrid retrieval."}
            ],
        }
    )

    assert parsed.answer_text == "Grounded uses hybrid retrieval."
    assert parsed.cited_evidence_ids == ["chunk-1"]
    assert parsed.citation_snippets == {
        "chunk-1": "Grounded uses hybrid retrieval."
    }


def test_parse_gemini_result_rejects_empty_array_citation_snippets() -> None:
    """Gemini parsing should fail cleanly when snippet arrays are empty."""

    with pytest.raises(GeminiGenerationError, match="invalid citation_snippets"):
        _parse_result(
            {
                "answer_text": "Grounded uses hybrid retrieval.",
                "cited_evidence_ids": ["chunk-1"],
                "citation_snippets": [],
            }
        )


def test_build_gemini_prompt_enforces_strict_refusal_and_minimal_evidence_payload() -> None:
    """The Gemini prompt should carry the hard refusal rule and a reduced evidence payload."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="The city purchased 12 electric vans from Voltara Mobility.",
            ),
        ],
    )

    prompt = _build_prompt(
        query_text="Which company supplied the vans?",
        evidence_package=evidence_package,
    )

    assert "I could not find the answer in the provided context." in prompt
    assert "If the answer exists explicitly in the evidence, you MUST extract it directly." in prompt
    assert "document_id=" not in prompt
    assert "chunk_role=" not in prompt
    assert "text=The city purchased 12 electric vans from Voltara Mobility." in prompt
    assert "answer_mode=exact_qa" in prompt


def test_build_gemini_prompt_uses_broader_mode_for_summary_queries() -> None:
    """Broader questions should use the summary/list prompt mode instead of exact extraction mode."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Explainable AI in Software Engineering\nThis paper examines trustworthy XAI methods for engineering teams.",
            ),
        ],
    )

    prompt = _build_prompt(
        query_text="What is the dataset about?",
        evidence_package=evidence_package,
    )

    assert "answer_mode=summary_list" in prompt
    assert "[section:" not in prompt


def test_generation_config_for_exact_qa_is_deterministic() -> None:
    """Exact QA should use deterministic provider settings for more stable extraction."""

    assert _generation_config_for_mode("exact_qa") == {
        "temperature": 0,
        "topP": 0.05,
        "topK": 1,
        "maxOutputTokens": 120,
    }


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
async def test_generate_answer_from_evidence_rejects_provider_banned_phrase_and_falls_back(monkeypatch) -> None:
    """Weak provider phrasing should be rejected before it reaches users."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="The city purchased 12 electric vans from Voltara Mobility.",
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
        return GroundedAnswerDraft(
            answer_text="I found relevant information about Voltara Mobility.",
            cited_evidence_ids=["chunk-1"],
            citation_snippets={"chunk-1": "The city purchased 12 electric vans from Voltara Mobility."},
            generator_provider="gemini:gemini-2.5-flash",
            support_coverage=1.0,
            source_diversity=1,
        )

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="Which company supplied the vans?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "The company is Voltara Mobility [E001]"
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


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_allows_two_chunk_provider_answer_for_start_end_lookup(
    monkeypatch,
) -> None:
    """Exact multi-part lookups should allow two cited chunks when both are needed."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-start", "chunk-end"],
        selected_evidence_ids=["chunk-start", "chunk-end"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-start",
                text="Pilot Overview\nIn January 2025, the city of Lydon launched the electric van pilot.",
            ),
            _evidence_item(
                citation_id="E002",
                chunk_id="chunk-end",
                text="Pilot Overview\nThe pilot lasted for six months and ended in June 2025.",
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
        return GroundedAnswerDraft(
            answer_text="It started in January 2025 and ended in June 2025.",
            cited_evidence_ids=["chunk-start", "chunk-end"],
            citation_snippets={
                "chunk-start": "In January 2025, the city of Lydon launched the electric van pilot.",
                "chunk-end": "The pilot lasted for six months and ended in June 2025.",
            },
            generator_provider="gemini:gemini-2.5-flash",
            support_coverage=1.0,
            source_diversity=1,
        )

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="When did the pilot start and end?",
        evidence_package=evidence_package,
    )

    assert draft.answer_text == "It started in January 2025 and ended in June 2025."
    assert draft.generator_provider == "gemini:gemini-2.5-flash"


@pytest.mark.asyncio()
async def test_generate_answer_from_evidence_rejects_heading_only_provider_collection_answer(monkeypatch) -> None:
    """Provider list answers should fall back when they mostly echo headings instead of grounded items."""

    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-paper-tools"],
        selected_evidence_ids=["chunk-paper-tools"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-paper-tools",
                text=(
                    "The What-If Tool demonstrates how visual analytics can support model debugging, "
                    "feature sensitivity analysis, and fairness inspection with low coding overhead. "
                    "Together with SHAP and LIME, it shows how XAI tooling is entering practical engineering workflows."
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
            answer_text="2. Methods, Technologies, and Tools [E001]",
            cited_evidence_ids=["chunk-paper-tools"],
            citation_snippets={
                "chunk-paper-tools": "2. Methods, Technologies, and Tools",
            },
            generator_provider="gemini:gemini-2.5-flash",
            support_coverage=1.0,
            source_diversity=1,
        )

    monkeypatch.setattr(
        "app.services.generation.generate_gemini_draft",
        fake_generate_gemini_draft,
    )

    draft = await generate_answer_from_evidence(
        query_text="What are the tools?",
        evidence_package=evidence_package,
    )

    assert "What-If Tool" in draft.answer_text
    assert draft.generator_provider == "local-grounded-v1:fallback_from_gemini_v1"
