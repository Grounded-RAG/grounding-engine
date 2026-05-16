"""Seed the nfcorpus BEIR dataset into the Grounded vector store for live retrieval benchmarks.

Usage:
    python -m scripts.seed_nfcorpus --limit 100 --dry-run
    python -m scripts.seed_nfcorpus --limit 500
    python -m scripts.seed_nfcorpus --clear  # wipe benchmark namespace first
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from qdrant_client.http import models as qdrant_models

from app.config import get_settings
from app.core.embeddings import embed_texts
from app.core.qdrant_client import get_qdrant_client, ensure_qdrant_collection


BENCHMARK_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
BENCHMARK_NAMESPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def chunk_text(text: str, max_tokens: int = 512) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        estimated_tokens = len(word) // 4 + 1
        if current_len + estimated_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(word)
        current_len += estimated_tokens

    if current:
        chunks.append(" ".join(current))
    return chunks


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


async def seed_nfcorpus(
    corpus_path: Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    clear_first: bool = False,
) -> dict:
    docs = []
    with corpus_path.open() as fh:
        for line in fh:
            entry = json.loads(line)
            docs.append(
                {
                    "doc_id": entry["_id"],
                    "title": entry.get("title", ""),
                    "text": entry.get("text", ""),
                }
            )
            if limit and len(docs) >= limit:
                break

    print(f"Loaded {len(docs)} documents from {corpus_path}")

    if dry_run:
        print(f"[DRY RUN] Would seed {len(docs)} documents")
        for doc in docs[:3]:
            chunks = chunk_text(doc["text"])
            print(f"  {doc['doc_id']}: {len(chunks)} chunks")
        return {"documents": len(docs), "dry_run": True}

    settings = get_settings()
    client = get_qdrant_client()
    collection = settings.qdrant_collection
    vector_size = settings.dense_embedding_dimensions
    ensure_qdrant_collection(vector_size=vector_size)

    if clear_first:
        print(f"Clearing benchmark namespace ({BENCHMARK_NAMESPACE_ID}) from {collection}...")
        query_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="namespace_id",
                    match=qdrant_models.MatchValue(value=str(BENCHMARK_NAMESPACE_ID)),
                ),
            ]
        )
        try:
            client.delete(
                collection_name=collection,
                points_selector=qdrant_models.FilterSelector(filter=query_filter),
                wait=True,
            )
            print("  Cleared.")
        except Exception as exc:
            print(f"  Warning: clear failed (collection may be empty): {exc}")

    all_points: list[qdrant_models.PointStruct] = []
    total_chunks = 0

    for doc in docs:
        title = doc["title"]
        text = doc["text"]
        doc_id = doc["doc_id"]

        combined_text = f"{title}\n{text}" if title else text
        raw_chunks = chunk_text(combined_text)

        texts_to_embed = raw_chunks
        try:
            embeddings = await embed_texts(texts_to_embed, purpose="document")
        except Exception as exc:
            print(f"  Warning: embedding failed for {doc_id}: {exc}")
            continue

        for i, (chunk_text_str, embedding) in enumerate(zip(raw_chunks, embeddings)):
            point_id = _point_id(f"{doc_id}-chunk-{i}")
            all_points.append(
                qdrant_models.PointStruct(
                    id=point_id,
                    vector=embedding.vector,
                    payload={
                        "tenant_id": str(BENCHMARK_TENANT_ID),
                        "namespace_id": str(BENCHMARK_NAMESPACE_ID),
                        "document_id": doc_id,
                        "chunk_id": f"{doc_id}-chunk-{i}",
                        "chunk_index": i,
                        "text": chunk_text_str,
                        "section_title": title,
                        "title": title,
                        "mime_type": "text/plain",
                        "token_count": len(chunk_text_str.split()) * 3 // 4,
                        "character_count": len(chunk_text_str),
                    },
                )
            )
        total_chunks += len(raw_chunks)

    if not all_points:
        print("No points to upsert.")
        return {"documents": len(docs), "chunks": 0}

    batch_size = 200
    indexed = 0
    for i in range(0, len(all_points), batch_size):
        batch = all_points[i : i + batch_size]
        client.upsert(collection_name=collection, points=batch, wait=True)
        indexed += len(batch)
        print(f"  Upserted batch {i // batch_size + 1}: {indexed}/{len(all_points)} points")

    print(f"Done. Seeded {len(docs)} docs, {total_chunks} chunks, {indexed} vector points.")
    return {"documents": len(docs), "chunks": total_chunks, "points": indexed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed nfcorpus into Grounded vector store.")
    parser.add_argument(
        "--corpus",
        default="nfcorpus/corpus.jsonl",
        help="Path to corpus.jsonl (relative to repo root or absolute).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to N documents (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without upserting anything.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing benchmark namespace before seeding.",
    )
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.is_absolute():
        corpus_path = (Path(__file__).parent.parent.parent.parent / args.corpus).resolve()

    if not corpus_path.exists():
        print(f"Error: corpus not found at {corpus_path}")
        return

    import asyncio
    result = asyncio.run(
        seed_nfcorpus(corpus_path, limit=args.limit, dry_run=args.dry_run, clear_first=args.clear)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()