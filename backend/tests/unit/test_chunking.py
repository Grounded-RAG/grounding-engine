"""Unit tests for deterministic chunking orchestration."""

from __future__ import annotations

import uuid

from app.pipeline.contracts import ChunkingConfig
from app.pipeline.orchestrator import build_chunk_manifest
from app.services.chunking import derive_chunk_manifest_key


def test_build_chunk_manifest_is_deterministic() -> None:
    """The same input should always produce the same chunk manifest."""

    document_id = uuid.uuid4()
    text = "one two three four five six seven eight nine ten"
    config = ChunkingConfig(max_tokens=4, overlap_tokens=1)

    manifest_one = build_chunk_manifest(
        document_id=document_id,
        text=text,
        source_artifact_key="artifact.txt",
        config=config,
    )
    manifest_two = build_chunk_manifest(
        document_id=document_id,
        text=text,
        source_artifact_key="artifact.txt",
        config=config,
    )

    assert manifest_one.to_payload() == manifest_two.to_payload()


def test_build_chunk_manifest_respects_token_windows_and_overlap() -> None:
    """Chunk windows should stay within the configured token limits."""

    manifest = build_chunk_manifest(
        document_id=uuid.uuid4(),
        text="one two three four five six seven eight nine",
        source_artifact_key="artifact.txt",
        config=ChunkingConfig(max_tokens=4, overlap_tokens=1),
    )

    assert [chunk.text for chunk in manifest.chunks] == [
        "one two three four",
        "four five six seven",
        "seven eight nine",
    ]
    assert all(chunk.token_count <= 4 for chunk in manifest.chunks)
    assert manifest.chunks[1].start_token == 3
    assert manifest.chunks[1].end_token == 6


def test_build_chunk_manifest_can_preserve_paragraph_boundaries() -> None:
    """Structure-aware chunking should prefer paragraph grouping over raw slicing."""

    manifest = build_chunk_manifest(
        document_id=uuid.uuid4(),
        text=(
            "Overview of the grounded system.\n\n"
            "Datasets provide the source of truth for retrieval.\n\n"
            "Agents answer using grounded evidence with citations."
        ),
        source_artifact_key="artifact.txt",
        config=ChunkingConfig(
            max_tokens=14,
            overlap_tokens=2,
            strategy="structure_aware_v1",
        ),
    )

    assert manifest.chunking_strategy == "structure_aware_v1"
    assert [chunk.text for chunk in manifest.chunks] == [
        "Overview of the grounded system.\n\nDatasets provide the source of truth for retrieval.",
        "for retrieval.\n\nAgents answer using grounded evidence with citations.",
    ]


def test_build_chunk_manifest_respects_heading_and_bullet_boundaries() -> None:
    """Structure-aware chunking should split resume-like headings and bullet lists more cleanly."""

    manifest = build_chunk_manifest(
        document_id=uuid.uuid4(),
        text=(
            "EDUCATION\n"
            "BSc in Software Engineering at Addis Ababa Science and Technology University.\n"
            "EXPERIENCE\n"
            "- AI Engineer at iCog Labs\n"
            "- Built grounded retrieval and citation workflows\n"
            "PROJECTS\n"
            "StyleCraft adaptive writing assistant."
        ),
        source_artifact_key="artifact.txt",
        config=ChunkingConfig(
            max_tokens=12,
            overlap_tokens=2,
            strategy="structure_aware_v1",
        ),
    )

    assert manifest.chunking_strategy == "structure_aware_v1"
    assert len(manifest.chunks) >= 3
    assert manifest.chunks[0].text.startswith("EDUCATION\nBSc in Software Engineering")
    assert manifest.chunks[0].section_title == "EDUCATION"
    assert manifest.chunks[0].chunk_role == "section_header"
    assert any("EXPERIENCE\n- AI Engineer at iCog Labs" in chunk.text for chunk in manifest.chunks)
    experience_chunk = next(
        chunk for chunk in manifest.chunks if "EXPERIENCE\n- AI Engineer at iCog Labs" in chunk.text
    )
    assert experience_chunk.section_title == "EXPERIENCE"
    assert experience_chunk.is_list_block is True
    assert any("PROJECTS\nStyleCraft adaptive writing assistant." in chunk.text for chunk in manifest.chunks)


def test_build_chunk_manifest_keeps_distinct_sections_separate_when_headings_change() -> None:
    """Structure-aware chunking should not merge adjacent headed sections into one chunk."""

    manifest = build_chunk_manifest(
        document_id=uuid.uuid4(),
        text=(
            "AWARDS\n"
            "Selected for Huawei Seeds for the Future.\n"
            "TECHNICAL SKILLS\n"
            "Python, Go, TypeScript, FastAPI.\n"
            "CERTIFICATES\n"
            "DeepLearning.AI specialization."
        ),
        source_artifact_key="artifact.txt",
        config=ChunkingConfig(
            max_tokens=128,
            overlap_tokens=8,
            strategy="structure_aware_v1",
        ),
    )

    assert any(chunk.text.startswith("AWARDS\n") for chunk in manifest.chunks)
    assert any(chunk.text.startswith("TECHNICAL SKILLS\n") for chunk in manifest.chunks)
    assert any(chunk.text.startswith("CERTIFICATES\n") for chunk in manifest.chunks)
    assert {
        chunk.section_slug
        for chunk in manifest.chunks
        if chunk.section_slug is not None
    } >= {"awards", "technical-skills", "certificates"}
    assert not any(
        "AWARDS" in chunk.text and "TECHNICAL SKILLS" in chunk.text
        for chunk in manifest.chunks
    )


def test_derive_chunk_manifest_key_uses_chunk_artifact_path() -> None:
    """Chunk manifests should live under the deterministic artifact prefix."""

    assert derive_chunk_manifest_key(
        "tenants/t1/namespaces/n1/documents/d1/source/manual.txt"
    ) == "tenants/t1/namespaces/n1/documents/d1/artifacts/chunks/manifest.json"
