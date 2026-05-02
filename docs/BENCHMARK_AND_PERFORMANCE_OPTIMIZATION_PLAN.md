# Benchmark And Performance Optimization Plan

## Goal

Create a reproducible benchmark that compares output quality, retrieval quality,
latency, cost, and component-level contribution across Naive RAG, Standard RAG,
Temporal RAG, and future advanced paths.

The benchmark should answer:

- Is Standard RAG actually better than Naive RAG?
- Which components improve retrieval and answer quality?
- Does Temporal RAG improve freshness-sensitive answers?
- Are better outputs worth the added latency and cost?
- Are citations actually supporting the answer?
- Does the system degrade correctly when evidence is missing?
- Which query types still fail most often?

## Benchmark Contract

Every benchmark variant should return the same result shape.

```json
{
  "run_id": "2026-05-02-standard-v1",
  "variant": "standard_hybrid",
  "query_id": "eval_001",
  "query": "What are the technical requirements?",
  "answer": "...",
  "retrieved_chunk_ids": [],
  "selected_evidence_ids": [],
  "citations": [],
  "metrics": {
    "precision_at_k": 0.0,
    "recall_at_k": 0.0,
    "mrr": 0.0,
    "ndcg_at_k": 0.0,
    "faithfulness": 0.0,
    "answer_relevancy": 0.0,
    "context_precision": 0.0,
    "context_recall": 0.0,
    "citation_accuracy": 0.0,
    "temporal_accuracy": 0.0
  },
  "performance": {
    "retrieval_ms": 0,
    "evidence_packaging_ms": 0,
    "answering_ms": 0,
    "verification_ms": 0,
    "total_latency_ms": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "estimated_cost_usd": 0.0
  },
  "behavior": {
    "degraded": false,
    "degraded_reasons": [],
    "unsupported_claims": [],
    "source_policy_violations": []
  }
}
```

## Benchmark Suites

Expand the current fixture at:

`backend/tests/evaluation/fixtures/rag_eval_testset.json`

Recommended suites:

| Suite | Purpose |
|---|---|
| `basic_fact_lookup` | Direct factual answers |
| `field_extraction` | Resume, profile, and policy extraction |
| `list_collection` | Lists, steps, benefits, requirements |
| `comparison` | Compare values, dates, entities |
| `multi_hop` | Requires multiple chunks |
| `temporal_freshness` | Newer evidence should beat stale evidence |
| `contradiction` | Conflicting evidence must be surfaced |
| `insufficient_evidence` | System should abstain or degrade |
| `conversation_followup` | Follow-up questions needing history |
| `source_policy` | Strict, Balanced, and Live grounding behavior |

Example temporal case:

```json
{
  "id": "temporal_001",
  "query": "What is the current refund window?",
  "query_type": "temporal_policy",
  "difficulty": "medium",
  "expected_answer": "The current refund window is 14 days.",
  "ground_truth_chunk_ids": ["policy_2026_chunk_03"],
  "stale_chunk_ids": ["policy_2024_chunk_02"],
  "ground_truth_statements": [
    "The current refund window is 14 days",
    "The 30-day refund policy was superseded"
  ],
  "expected_behavior": "prefer_fresh_evidence",
  "domain": "policy"
}
```

## Benchmark Variants

Initial runnable variants:

| Variant | Meaning |
|---|---|
| `naive_dense_only` | Existing baseline from `retrieval_baseline.py` |
| `standard_hybrid` | Current Standard query path |
| `standard_no_query_plan` | Ablation test |
| `standard_no_rerank` | Ablation test |
| `standard_no_evidence_packaging` | Ablation test |

Future variants:

| Variant | Meaning |
|---|---|
| `enterprise_temporal_rag` | Freshness-aware Enterprise retrieval |
| `enterprise_temporal_no_freshness` | Ablation for temporal scoring |
| `critical_verified` | Verification and corrective path |
| `critical_no_verifier` | Ablation for verifier |
| `adaptive_strict` | Dataset-only grounding |
| `adaptive_balanced` | Dataset plus disclosed model knowledge |
| `adaptive_live` | Dataset plus live or external context |

## Metrics

### Retrieval Metrics

| Metric | Purpose |
|---|---|
| `Precision@K` | How much retrieved context was useful |
| `Recall@K` | Whether required evidence was retrieved |
| `MRR` | Whether the first relevant chunk ranked early |
| `NDCG@K` | Whether evidence ranking was correct |
| `Context Precision` | Whether selected context was useful |
| `Context Recall` | Whether selected context contained all needed facts |

### Answer Metrics

| Metric | Purpose |
|---|---|
| `Faithfulness` | Whether answer claims are supported |
| `Answer Relevancy` | Whether answer addresses the query |
| `Citation Accuracy` | Whether citations support the answer |
| `Unsupported Claim Rate` | Hallucination risk |
| `Abstention Correctness` | Whether the system degraded correctly |

### Temporal Metrics

| Metric | Purpose |
|---|---|
| `Temporal Accuracy` | Whether fresh evidence was preferred correctly |
| `Stale Evidence Rate` | How often outdated evidence was used |
| `Conflict Handling Score` | Whether contradictory evidence was surfaced |

### Performance Metrics

| Metric | Purpose |
|---|---|
| `total_latency_ms` | End-to-end speed |
| `retrieval_ms` | Retrieval cost |
| `evidence_packaging_ms` | Evidence selection cost |
| `answering_ms` | Generation cost |
| `verification_ms` | Verifier overhead |
| `trace_persistence_ms` | Observability overhead |
| `prompt_tokens` | Input token cost |
| `completion_tokens` | Output token cost |
| `estimated_cost_usd` | Operational cost |

## Current Implementation Status

The benchmark has two execution modes:

- Fixture mode: deterministic local replay for CI-safe benchmark development.
- Live mode: real database/vector-store-backed runners for Naive and Standard paths.

`backend/tests/evaluation/generate_comparison_report.py` no longer creates fake
"improved Standard" results. It delegates to the shared benchmark runner. By
default it uses fixture variants so it can run without external services. To call
the real Standard query pipeline, pass a `BenchmarkExecutionContext` with a live
session, tenant context, and namespace, then include `standard_hybrid_live` in the
variant list.

Implemented pieces:

- `run_naive_rag()` remains available through `naive_dense_only_live`.
- `execute_standard_query()` is available through `standard_hybrid_live`.
- Live Standard extracts persisted `QueryTrace` data for retrieved chunks,
  selected evidence, citations, answer text, and timings.
- The old fake `standard_chunks = ...` path has been removed.

## Ablation Tests

Ablation testing proves which component creates the quality improvement.

| Component | Compare |
|---|---|
| Sparse retrieval | `standard_hybrid` vs `standard_no_sparse` |
| Dense retrieval | `standard_hybrid` vs `standard_no_dense` |
| RRF fusion | `standard_hybrid` vs `standard_no_rrf` |
| Query planning | `standard_hybrid` vs `standard_no_query_plan` |
| Reranking | `standard_hybrid` vs `standard_no_rerank` |
| Evidence packaging | `standard_hybrid` vs `standard_no_evidence_packaging` |
| Temporal scoring | `enterprise_temporal_rag` vs `enterprise_no_temporal` |
| Verification | `critical_verified` vs `critical_no_verifier` |

Example final claim:

> Temporal scoring improved temporal correctness from 0.42 to 0.81, but
> increased P95 latency by 620ms.

## Output Files

Each benchmark run should generate:

| File | Purpose |
|---|---|
| `benchmark_results.jsonl` | One record per query per variant |
| `benchmark_summary.json` | Aggregated metrics by variant, type, difficulty, and domain |
| `benchmark_report.md` | Human-readable report |

Recommended output path:

`reports/benchmark/`

Example:

```text
reports/benchmark/benchmark_results.jsonl
reports/benchmark/benchmark_summary.json
reports/benchmark/benchmark_report.md
```

## Human Report Format

The Markdown report should include:

| Variant | RAGAS | Recall@5 | Faithfulness | Citation Accuracy | Temporal Accuracy | P95 Latency | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|

Query-type breakdown:

| Query Type | Best Variant | Worst Variant | Main Failure |
|---|---|---|---|

Component contribution:

| Component | Quality Gain | Latency Cost | Recommendation |
|---|---:|---:|---|

## Pass/Fail Gates

Suggested minimum gates:

| Metric | Minimum |
|---|---:|
| `Recall@5` | `>= 0.80` |
| `MRR` | `>= 0.70` |
| `Faithfulness` | `>= 0.85` |
| `Citation Accuracy` | `>= 0.90` |
| `Unsupported Claim Rate` | `<= 0.05` |
| `Temporal Accuracy` | `>= 0.80` for temporal suite |

Suggested P95 latency budgets:

| Tier | P95 Budget |
|---|---:|
| Naive | `< 1s` |
| Standard | `< 2s` |
| Enterprise / Temporal | `< 4s` |
| Critical / Verified | `< 8-15s` |

## Recommended File-Level Work

Existing files to update:

| File | Change |
|---|---|
| `backend/tests/evaluation/fixtures/rag_eval_testset.json` | Expand or split benchmark datasets |
| `backend/tests/evaluation/generate_comparison_report.py` | Replace synthetic Standard output with real runner |
| `backend/app/services/evaluation_metrics.py` | Add citation, abstention, temporal, and unsupported-claim metrics |
| `backend/app/services/retrieval_baseline.py` | Keep baseline, expose consistent result schema |
| `backend/app/services/query.py` | Reuse trace timings |
| `backend/app/models/query_trace.py` | Use existing trace fields for benchmark extraction |

Potential new files:

| File | Purpose |
|---|---|
| `backend/tests/evaluation/benchmark_runner.py` | Runs all variants against all cases |
| `backend/tests/evaluation/benchmark_variants.py` | Variant registry and ablations |
| `backend/tests/evaluation/benchmark_schema.py` | Shared result dataclasses |
| `backend/tests/evaluation/benchmark_report.py` | Markdown and JSON report generation |
| `backend/tests/evaluation/fixtures/temporal_cases.json` | Temporal benchmark data |
| `backend/tests/evaluation/fixtures/contradiction_cases.json` | Conflict benchmark data |

## Execution Order

1. Define shared benchmark schema.
2. Add real Standard runner.
3. Add JSONL result output.
4. Add summary aggregation.
5. Add citation, abstention, temporal, and unsupported-claim metrics.
6. Expand benchmark fixtures.
7. Add ablation variants.
8. Generate Markdown report.
9. Add CI-safe smoke benchmark.
10. Add full local/manual benchmark command.

## Target Command

The final benchmark should run with a command like:

```bash
python -m tests.evaluation.benchmark_runner \
  --suites basic,temporal,contradiction \
  --variants naive_dense_only,standard_hybrid,standard_no_rerank \
  --output reports/benchmark
```

Expected output:

```text
reports/benchmark/benchmark_results.jsonl
reports/benchmark/benchmark_summary.json
reports/benchmark/benchmark_report.md
```

## Success Criteria

This benchmark is successful when it clearly shows:

- Whether Standard beats Naive.
- Which component improves retrieval most.
- Whether Temporal RAG beats non-temporal retrieval on freshness-sensitive cases.
- Whether higher-quality outputs justify latency and cost.
- Whether citations support the answer.
- Whether the system degrades correctly when evidence is missing.
- Which query types still fail most often.
