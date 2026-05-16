"""Benchmark variant registry and runnable fixture/live runners."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from tests.evaluation.benchmark_schema import (
    BenchmarkBehavior,
    BenchmarkCase,
    BenchmarkMetrics,
    BenchmarkPerformance,
    BenchmarkResult,
)


@dataclass(frozen=True)
class BenchmarkExecutionContext:
    """Optional live dependencies for database-backed benchmark variants."""

    session: Any | None = None
    tenant_context: Any | None = None
    tenant_id: UUID | None = None
    namespace_id: UUID | None = None


class BenchmarkVariant(Protocol):
    """Protocol implemented by all benchmark variants."""

    name: str

    async def run(
        self,
        *,
        case: BenchmarkCase,
        run_id: str,
        context: BenchmarkExecutionContext | None = None,
    ) -> BenchmarkResult:
        """Run this variant against one case."""


@dataclass(frozen=True)
class FixtureReplayVariant:
    """Deterministic fixture-backed variant for local benchmark development."""

    name: str
    use_query_terms: bool = True
    use_temporal_score: bool = False
    use_evidence_packaging: bool = True
    max_retrieved: int = 5
    max_evidence: int = 3

    async def run(
        self,
        *,
        case: BenchmarkCase,
        run_id: str,
        context: BenchmarkExecutionContext | None = None,
    ) -> BenchmarkResult:
        started_at = time.perf_counter()
        chunks = self._rank_chunks(case)
        retrieved = chunks[: self.max_retrieved]
        evidence = self._select_evidence(case, retrieved)
        answer = self._compose_answer(case, evidence)
        degraded = case.expected_behavior == "abstain" and not evidence

        result = BenchmarkResult(
            run_id=run_id,
            variant=self.name,
            query_id=case.id,
            query=case.query,
            answer=answer,
            retrieved_chunk_ids=[str(chunk["chunk_id"]) for chunk in retrieved],
            selected_evidence_ids=[str(chunk["chunk_id"]) for chunk in evidence],
            retrieved_chunks=[str(chunk.get("text", "")) for chunk in retrieved],
            citations=[
                {
                    "citation_id": f"E{index:03d}",
                    "chunk_id": str(chunk["chunk_id"]),
                    "quote": str(chunk.get("text", "")),
                }
                for index, chunk in enumerate(evidence, start=1)
            ],
            performance=BenchmarkPerformance(
                total_latency_ms=int((time.perf_counter() - started_at) * 1000),
            ),
            behavior=BenchmarkBehavior(
                degraded=degraded,
                degraded_reasons=["NO_GROUNDED_EVIDENCE"] if degraded else [],
            ),
            query_type=case.query_type,
            difficulty=case.difficulty,
            domain=case.domain,
            suite=case.suite,
        )
        result.metrics = await calculate_benchmark_metrics(case, result)
        return result

    def _rank_chunks(self, case: BenchmarkCase) -> list[dict[str, Any]]:
        chunks = list(case.candidate_chunks)
        if not chunks:
            return []
        if not self.use_query_terms and not self.use_temporal_score:
            return chunks

        query_terms = _terms(case.query)

        def score(chunk: dict[str, Any]) -> tuple[float, str]:
            text_terms = _terms(str(chunk.get("text", "")))
            lexical_score = len(query_terms & text_terms) if self.use_query_terms else 0
            temporal_score = _date_score(str(chunk.get("document_date", ""))) if self.use_temporal_score else 0.0
            return lexical_score + temporal_score, str(chunk.get("chunk_id", ""))

        return sorted(chunks, key=lambda chunk: (-score(chunk)[0], score(chunk)[1]))

    def _select_evidence(
        self,
        case: BenchmarkCase,
        retrieved: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not self.use_evidence_packaging:
            return retrieved[: self.max_retrieved]
        if case.expected_behavior == "abstain":
            relevant = set(case.ground_truth_chunk_ids)
            return [chunk for chunk in retrieved if str(chunk.get("chunk_id")) in relevant]
        if self.use_temporal_score and case.stale_chunk_ids:
            stale = set(case.stale_chunk_ids)
            fresh = set(case.ground_truth_chunk_ids)
            fresh_hits = [chunk for chunk in retrieved if str(chunk.get("chunk_id")) in fresh]
            if fresh_hits:
                non_stale_hits = [chunk for chunk in retrieved if str(chunk.get("chunk_id")) not in stale]
                return non_stale_hits[: self.max_evidence]
        return retrieved[: self.max_evidence]

    def _compose_answer(self, case: BenchmarkCase, evidence: list[dict[str, Any]]) -> str:
        if case.expected_behavior == "abstain" and not evidence:
            return "The provided evidence does not contain enough information to answer."
        if case.expected_behavior == "surface_conflict" and len(evidence) >= 2:
            return "The documents conflict: " + " ".join(
                f"[E{index:03d}] {chunk.get('text', '')}"
                for index, chunk in enumerate(evidence, start=1)
            )
        if not evidence:
            return "I don't have enough information to answer that."
        if case.expected_answer:
            return f"{case.expected_answer} [E001]"
        return " ".join(str(chunk.get("text", "")) for chunk in evidence)


@dataclass(frozen=True)
class LiveNaiveDenseVariant:
    """Database/vector-store-backed Naive RAG variant."""

    name: str = "naive_dense_only_live"

    async def run(
        self,
        *,
        case: BenchmarkCase,
        run_id: str,
        context: BenchmarkExecutionContext | None = None,
    ) -> BenchmarkResult:
        if context is None or context.tenant_id is None or context.namespace_id is None:
            raise ValueError("Live Naive benchmark requires tenant_id and namespace_id.")
        from app.services.retrieval_baseline import run_naive_rag

        started_at = time.perf_counter()
        output = await run_naive_rag(
            query_text=case.query,
            tenant_id=context.tenant_id,
            namespace_id=context.namespace_id,
            session=context.session,
        )
        chunks = list(output.get("chunks", []))
        result = BenchmarkResult(
            run_id=run_id,
            variant=self.name,
            query_id=case.id,
            query=case.query,
            answer=str(output.get("answer", "")),
            retrieved_chunk_ids=[str(chunk.chunk_id) for chunk in chunks],
            selected_evidence_ids=[str(chunk.chunk_id) for chunk in chunks],
            retrieved_chunks=[str(chunk.text) for chunk in chunks],
            performance=BenchmarkPerformance(
                retrieval_ms=int((time.perf_counter() - started_at) * 1000),
                total_latency_ms=int((time.perf_counter() - started_at) * 1000),
            ),
            query_type=case.query_type,
            difficulty=case.difficulty,
            domain=case.domain,
            suite=case.suite,
        )
        result.metrics = await calculate_benchmark_metrics(case, result)
        return result


@dataclass(frozen=True)
class LiveStandardHybridVariant:
    """Database-backed Standard RAG variant using the actual query service."""

    name: str = "standard_hybrid_live"

    async def run(
        self,
        *,
        case: BenchmarkCase,
        run_id: str,
        context: BenchmarkExecutionContext | None = None,
    ) -> BenchmarkResult:
        if (
            context is None
            or context.session is None
            or context.tenant_context is None
            or context.namespace_id is None
        ):
            raise ValueError(
                "Live Standard benchmark requires session, tenant_context, and namespace_id."
            )
        from app.schemas.query import QueryRequest
        from app.services.query import execute_standard_query

        query_result = await execute_standard_query(
            session=context.session,
            tenant_context=context.tenant_context,
            query_request=QueryRequest(namespace_id=context.namespace_id, query=case.query),
        )
        trace = await _get_trace(context.session, query_result.trace_id)
        stage_latencies = dict(trace.stage_latencies_ms or {})
        token_usage = dict(trace.token_usage or {})
        citations = list(trace.citations or [])
        result = BenchmarkResult(
            run_id=run_id,
            variant=self.name,
            query_id=case.id,
            query=case.query,
            answer=query_result.response.answer,
            retrieved_chunk_ids=[str(value) for value in trace.retrieved_chunk_ids],
            selected_evidence_ids=[str(value) for value in trace.selected_evidence_ids],
            retrieved_chunks=[str(citation.get("quote", "")) for citation in citations],
            citations=citations,
            performance=BenchmarkPerformance(
                retrieval_ms=int(stage_latencies.get("retrieval_ms", 0)),
                evidence_packaging_ms=int(stage_latencies.get("evidence_packaging_ms", 0)),
                answering_ms=int(stage_latencies.get("answering_ms", 0)),
                trace_persistence_ms=int(stage_latencies.get("trace_persistence_ms", 0)),
                total_latency_ms=int(trace.total_latency_ms),
                prompt_tokens=int(token_usage.get("prompt_tokens", 0)),
                completion_tokens=int(token_usage.get("completion_tokens", 0)),
            ),
            behavior=BenchmarkBehavior(
                degraded=query_result.response.verification_status == "degraded",
                degraded_reasons=list(query_result.response.degraded_reasons),
            ),
            query_type=case.query_type,
            difficulty=case.difficulty,
            domain=case.domain,
            suite=case.suite,
        )
        result.metrics = await calculate_benchmark_metrics(case, result)
        return result


async def _get_trace(session: Any, trace_id):
    from sqlalchemy import select

    from app.models import QueryTrace

    result = await session.execute(select(QueryTrace).where(QueryTrace.trace_id == trace_id))
    trace = result.scalar_one()
    return trace


async def calculate_benchmark_metrics(
    case: BenchmarkCase,
    result: BenchmarkResult,
) -> BenchmarkMetrics:
    """Calculate shared metrics for a canonical benchmark result."""

    cited_chunk_ids = [str(citation.get("chunk_id", "")) for citation in result.citations]
    selected_ids = result.selected_evidence_ids or cited_chunk_ids
    precision_at_k = _precision_at_k(result.retrieved_chunk_ids, case.ground_truth_chunk_ids, 5)
    recall_at_k = _recall_at_k(result.retrieved_chunk_ids, case.ground_truth_chunk_ids, 5)
    mrr = _mrr(result.retrieved_chunk_ids, case.ground_truth_chunk_ids)
    ndcg_at_k = _ndcg_at_k(result.retrieved_chunk_ids, case.ground_truth_chunk_ids, 5)
    faithfulness = _faithfulness(result.answer, result.retrieved_chunks)
    answer_relevancy = _answer_relevancy(case.query, result.answer)
    context_precision = _context_precision(case.query, result.retrieved_chunks)
    context_recall = _context_recall(case.expected_answer, result.retrieved_chunks)
    ragas_components = [context_precision, faithfulness, answer_relevancy]
    if case.expected_answer:
        ragas_components.append(context_recall)
    return BenchmarkMetrics(
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        mrr=mrr,
        ndcg_at_k=ndcg_at_k,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_precision=context_precision,
        context_recall=context_recall,
        citation_accuracy=_citation_accuracy(cited_chunk_ids, case.ground_truth_chunk_ids),
        temporal_accuracy=_temporal_accuracy(
            selected_ids,
            case.ground_truth_chunk_ids,
            case.stale_chunk_ids,
        ),
        stale_evidence_rate=_stale_evidence_rate(selected_ids, case.stale_chunk_ids),
        abstention_correctness=_abstention_correctness(
            expected_behavior=case.expected_behavior,
            degraded=result.behavior.degraded,
            answer=result.answer,
        ),
        unsupported_claim_rate=1.0 - faithfulness if result.answer else 0.0,
        ragas_score=sum(ragas_components) / len(ragas_components),
        ares_score=(context_precision + faithfulness + answer_relevancy) / 3.0,
    )


def get_fixture_variants() -> dict[str, BenchmarkVariant]:
    """Return deterministic variants available without external services."""

    return {
        "naive_dense_only": FixtureReplayVariant(
            name="naive_dense_only",
            use_query_terms=False,
            use_temporal_score=False,
            use_evidence_packaging=False,
        ),
        "standard_hybrid": FixtureReplayVariant(
            name="standard_hybrid",
            use_query_terms=True,
            use_temporal_score=False,
            use_evidence_packaging=True,
        ),
        "standard_no_query_plan": FixtureReplayVariant(
            name="standard_no_query_plan",
            use_query_terms=False,
            use_temporal_score=False,
            use_evidence_packaging=True,
        ),
        "standard_no_rerank": FixtureReplayVariant(
            name="standard_no_rerank",
            use_query_terms=False,
            use_temporal_score=False,
            use_evidence_packaging=True,
        ),
        "standard_no_evidence_packaging": FixtureReplayVariant(
            name="standard_no_evidence_packaging",
            use_query_terms=True,
            use_temporal_score=False,
            use_evidence_packaging=False,
        ),
        "enterprise_temporal_rag": FixtureReplayVariant(
            name="enterprise_temporal_rag",
            use_query_terms=True,
            use_temporal_score=True,
            use_evidence_packaging=True,
        ),
        "enterprise_temporal_no_freshness": FixtureReplayVariant(
            name="enterprise_temporal_no_freshness",
            use_query_terms=True,
            use_temporal_score=False,
            use_evidence_packaging=True,
        ),
    }


def get_live_variants() -> dict[str, BenchmarkVariant]:
    """Return variants that require live database/vector-store dependencies."""

    return {
        "naive_dense_only_live": LiveNaiveDenseVariant(),
        "standard_hybrid_live": LiveStandardHybridVariant(),
    }


def get_variants(*, include_live: bool = False) -> dict[str, BenchmarkVariant]:
    variants = get_fixture_variants()
    if include_live:
        variants.update(get_live_variants())
    return variants


def _terms(text: str) -> set[str]:
    normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "to",
        "of",
        "and",
        "or",
        "what",
        "which",
        "now",
        "current",
    }
    return {token for token in normalized.split() if len(token) > 2 and token not in stopwords}


def _date_score(value: str) -> float:
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return 0.0
    return parsed.timestamp() / 1_000_000_000


def _precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(relevant_ids)) / k


def _recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(relevant_ids)) / len(set(relevant_ids))


def _mrr(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    relevant = set(relevant_ids)
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def _ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    from math import log2

    if not relevant_ids:
        return 0.0
    relevant = set(relevant_ids)
    dcg = sum(
        1.0 / log2(rank + 1)
        for rank, chunk_id in enumerate(retrieved_ids[:k], start=1)
        if chunk_id in relevant
    )
    ideal_count = min(len(relevant), k)
    idcg = sum(1.0 / log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / idcg if idcg else 0.0


def _faithfulness(answer: str, contexts: list[str]) -> float:
    answer_terms = {term for term in _terms(answer) if len(term) > 3}
    if not answer_terms:
        return 0.0
    context_text = " ".join(contexts).casefold()
    supported = sum(1 for term in answer_terms if term in context_text)
    return supported / len(answer_terms)


def _answer_relevancy(question: str, answer: str) -> float:
    question_terms = _terms(question)
    answer_terms = _terms(answer)
    if not question_terms:
        return 0.0
    return len(question_terms & answer_terms) / len(question_terms)


def _context_precision(question: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    question_terms = _terms(question)
    relevant_count = sum(1 for context in contexts if question_terms & _terms(context))
    return relevant_count / len(contexts)


def _context_recall(expected_answer: str | None, contexts: list[str]) -> float:
    if not expected_answer:
        return 0.0
    expected_terms = _terms(expected_answer)
    if not expected_terms:
        return 0.0
    context_terms = _terms(" ".join(contexts))
    return len(expected_terms & context_terms) / len(expected_terms)


def _citation_accuracy(cited_chunk_ids: list[str], relevant_chunk_ids: list[str]) -> float:
    if not cited_chunk_ids:
        return 0.0 if relevant_chunk_ids else 1.0
    relevant = set(relevant_chunk_ids)
    if not relevant:
        return 0.0
    return len(set(cited_chunk_ids) & relevant) / len(set(cited_chunk_ids))


def _temporal_accuracy(
    selected_chunk_ids: list[str],
    fresh_chunk_ids: list[str],
    stale_chunk_ids: list[str],
) -> float:
    if not fresh_chunk_ids and not stale_chunk_ids:
        return 1.0  # no temporal signal — treat as correct
    selected = set(selected_chunk_ids)
    if selected & set(stale_chunk_ids):
        return 0.0
    return 1.0 if selected & set(fresh_chunk_ids) else 0.0


def _stale_evidence_rate(selected_chunk_ids: list[str], stale_chunk_ids: list[str]) -> float:
    if not selected_chunk_ids:
        return 0.0
    return len(set(selected_chunk_ids) & set(stale_chunk_ids)) / len(set(selected_chunk_ids))


def _abstention_correctness(*, expected_behavior: str | None, degraded: bool, answer: str) -> float:
    if expected_behavior != "abstain":
        return 0.0
    normalized = answer.casefold()
    abstained = degraded or any(
        phrase in normalized
        for phrase in ("does not contain", "not enough information", "could not find", "insufficient")
    )
    return 1.0 if abstained else 0.0
