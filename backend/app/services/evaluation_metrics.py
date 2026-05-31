"""Retrieval and generation evaluation metrics for the grounding engine."""

from __future__ import annotations

import math


def precision_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    *,
    k: int | None = None,
) -> float:
    """Fraction of top-k retrieved items that are relevant.

    Returns 0.0 when retrieved_ids is empty or k < 1.
    """
    top = retrieved_ids[:k] if k is not None else retrieved_ids
    if not top:
        return 0.0
    hits = sum(1 for chunk_id in top if chunk_id in relevant_ids)
    return hits / len(top)


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    *,
    k: int | None = None,
) -> float:
    """Fraction of relevant items found in top-k retrieved items.

    Returns 0.0 when relevant_ids is empty.
    Returns 1.0 when relevant_ids is empty and we divide by zero (vacuously true).
    """
    if not relevant_ids:
        return 0.0
    top = retrieved_ids[:k] if k is not None else retrieved_ids
    hits = sum(1 for chunk_id in top if chunk_id in relevant_ids)
    return hits / len(relevant_ids)


def reciprocal_rank(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """Reciprocal rank of the first relevant item in the list.

    Returns 0.0 when no relevant item is found.
    """
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    *,
    k: int | None = None,
) -> float:
    """Normalized Discounted Cumulative Gain at k (binary relevance).

    Uses log base-2 discount: gain_i = rel_i / log2(i + 1).
    Returns 0.0 when relevant_ids is empty.
    """
    if not relevant_ids:
        return 0.0

    top = retrieved_ids[:k] if k is not None else retrieved_ids

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(top, start=1)
        if chunk_id in relevant_ids
    )

    ideal_len = min(len(relevant_ids), len(top) if top else len(retrieved_ids))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_len + 1))

    return dcg / idcg if idcg > 0.0 else 0.0


def grounding_f1(
    cited_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """F1 between cited evidence chunk IDs and ground-truth relevant IDs.

    Precision = fraction of cited IDs that are relevant.
    Recall    = fraction of relevant IDs that were cited.
    F1        = harmonic mean of precision and recall.

    Returns 0.0 when cited_ids and relevant_ids are both empty.
    """
    if not cited_ids and not relevant_ids:
        return 0.0

    cited_set = set(cited_ids)
    p = len(cited_set & relevant_ids) / len(cited_set) if cited_set else 0.0
    r = len(cited_set & relevant_ids) / len(relevant_ids) if relevant_ids else 0.0

    if p + r == 0.0:
        return 0.0
    return 2 * p * r / (p + r)


def faithfulness_score(
    answer_sentences: list[str],
    evidence_texts: list[str],
) -> float:
    """Rough lexical faithfulness: fraction of answer sentences that have
    at least one matching evidence token run.

    Uses simple token-overlap heuristic. Higher values mean more
    answer content is grounded in evidence. Returns 0.0 for empty input.
    """
    if not answer_sentences:
        return 0.0

    combined_evidence = " ".join(evidence_texts).lower().split()
    evidence_tokens = set(combined_evidence)

    supported = 0
    for sentence in answer_sentences:
        sentence_tokens = set(sentence.lower().split())
        meaningful = {t for t in sentence_tokens if len(t) > 3}
        if not meaningful:
            supported += 1
            continue
        overlap = meaningful & evidence_tokens
        if len(overlap) / len(meaningful) >= 0.5:
            supported += 1

    return supported / len(answer_sentences)
