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


def test_derive_chunk_manifest_key_uses_chunk_artifact_path() -> None:
    """Chunk manifests should live under the deterministic artifact prefix."""

    assert derive_chunk_manifest_key(
        "tenants/t1/namespaces/n1/documents/d1/source/manual.txt"
    ) == "tenants/t1/namespaces/n1/documents/d1/artifacts/chunks/manifest.json"
