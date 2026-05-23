# Grounding Engine Benchmarking Plan

This README turns the earlier benchmarking notes into an executable evaluation plan for the Grounding Engine. The goal is to prove that the system is not only functional, but measurably better than a naive RAG baseline, traceable under failure, and ready to support Standard, Enterprise, and future Critical-tier claims.

## Goals

Benchmarking should answer five questions:

1. Does the system retrieve the right evidence?
2. Does Enterprise improve hard-query retrieval over Standard?
3. Are generated answers faithful to cited evidence?
4. Are citations valid, useful, and inspectable?
5. What are the latency and cost tradeoffs of deeper retrieval and generation?

## Evaluation Tiers

### Naive Baseline

Use this as the comparison floor.

- simple vector or sparse retrieval only
- top-k chunks passed directly to generation
- no query planning
- no reranking
- no freshness scoring
- no evidence packaging policy
- no provider fallback repair

### Standard

Standard is the main grounded baseline.

- query classification and lightweight query planning
- dense retrieval rollout path
- evidence packaging
- grounded generation
- citation validation
- degraded responses when evidence is insufficient
- trace and run inspection

### Enterprise

Enterprise should show measurable uplift on hard queries.

- deeper query planning for eligible queries
- controlled decomposition
- reranking where enabled
- freshness-aware scoring
- stronger evidence selection
- richer trace metadata
- `Thinking` mode path

### Critical

Critical is now live behind `Verified`, and benchmarks should measure its
verification and recovery behavior directly.

- verifier / critic loop
- corrective retrieval
- claim-by-claim verification
- stricter acceptance and rejection policies
- `Verified` mode activation

## Metrics

### Retrieval Metrics

- `precision@k`: fraction of retrieved chunks that are relevant
- `recall@k`: fraction of known relevant chunks retrieved
- `nDCG@k`: ranking quality when relevance labels have grades
- `MRR`: how early the first relevant chunk appears
- evidence diversity: number of useful documents/sections represented

### Answer Metrics

- faithfulness: answer claims are supported by evidence
- answer completeness: answer covers required parts of the question
- citation validity: cited chunk IDs exist and citation snippets are grounded
- citation usefulness: citations point to the best supporting evidence, not nearby noise
- refusal quality: unsupported questions degrade instead of hallucinating

### Operational Metrics

- end-to-end latency
- retrieval latency
- reranker latency
- generation latency
- provider fallback rate
- citation repair rate
- cost per request where provider cost data is available

## Benchmark Suites

### 1. Standard Quality Suite

Purpose: keep the Standard baseline stable.

Existing entry point:

```bash
pytest backend/tests/evaluation/test_standard_quality.py
```

Fixture source:

```text
backend/tests/evaluation/fixtures/standard_quality_cases.json
```

Coverage should include:

- exact lookup questions
- definition and explanation questions
- list extraction
- arithmetic from cited evidence
- unsupported-question refusals
- citation validation

### 2. Pilot Scenario Suite

Purpose: preserve the original advisor/demo scenario behavior.

Existing entry point:

```bash
pytest backend/tests/evaluation/test_standard_pilot_eval.py
```

Coverage should include the known pilot questions and expected answer fragments.

### 3. Enterprise Benchmark Suite

Purpose: prove Enterprise is better than Standard for harder queries.

Existing entry point:

```bash
pytest backend/tests/evaluation/test_enterprise_benchmarks.py
```

Coverage should include:

- planner effectiveness
- query rewrite usefulness
- reranker uplift
- temporal/freshness scoring uplift
- multi-document comparison questions
- multi-part questions requiring broader evidence coverage

### 4. Live Provider Smoke Suite

Purpose: validate behavior under real Gemini/OpenAI-compatible provider conditions.

Coverage should include:

- provider success path
- provider rate-limit fallback
- citation snippet repair
- fallback generation quality
- degraded response behavior
- run trace inspection after generation

Recommended live smoke questions:

- `What is continual learning? How does it work?`
- `What is catastrophic forgetting?`
- `What are common continual learning methods?`
- `What is the stability-plasticity tradeoff?`
- `Summarize the attached paper.`

## Manual Swagger Flow

Use `docs/SWAGGER_TEST_FLOW.md` for reviewer-friendly manual testing.

Enterprise-specific additions:

1. Call `GET /v1/capabilities` and verify `thinking` is enabled.
2. Run `POST /v1/agents/{agent_id}/chat` with `mode = "thinking"`.
3. Ask a hard ambiguous or multi-part question.
4. Call `GET /v1/runs/{run_id}`.
5. Verify the run shows routing, retrieval, evidence, and generation metadata.

## Trace Requirements

Every benchmarked query should make the following inspectable:

- query kind
- final answer mode
- attribute terms
- semantic tags
- context terms
- retrieval query variants
- selected evidence package
- generation provider
- provider fallback usage
- citation repair events
- confidence and degraded reasons

Recent observability events added for this purpose:

- `query_identified`
- `evidence_package_selected`
- `gemini_citation_snippet_repaired`

## Reporting Format

Use one table for aggregate metrics:

| System | Query Set | Precision@k | Recall@k | nDCG@k | Faithfulness | Citation Validity | Avg Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Naive | Standard quality | TBD | TBD | TBD | TBD | TBD | TBD |
| Standard | Standard quality | TBD | TBD | TBD | TBD | TBD | TBD |
| Enterprise | Hard queries | TBD | TBD | TBD | TBD | TBD | TBD |

Use a second table for failure analysis:

| Query | Expected Behavior | Actual Behavior | Failure Type | Root Cause | Fix / Follow-up |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD |

## Benchmark Execution Checklist

1. Install backend dev dependencies.
2. Start required services: database, Redis if needed, Qdrant, backend.
3. Ingest the benchmark datasets from a clean state.
4. Run Standard evaluation tests.
5. Run Enterprise benchmark tests.
6. Run live provider smoke tests when provider keys are configured.
7. Export run traces for failures and borderline cases.
8. Update metric tables and failure-analysis notes.
9. Compare Standard against naive baseline and Enterprise against Standard.
10. Decide whether changes are regressions, improvements, or inconclusive.

## Definition Of Done

Benchmarking is ready for final reporting when:

1. Standard has stable regression coverage across core query types.
2. Enterprise shows measurable uplift on hard queries.
3. Citation validity failures are rare, logged, and explainable.
4. Provider fallback behavior is tested and traceable.
5. Latency and quality tradeoffs are documented.
6. Failure cases are analyzed, not hidden.
7. The final report can show clear baseline-vs-improved evidence.
