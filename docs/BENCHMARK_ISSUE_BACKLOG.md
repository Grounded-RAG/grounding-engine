# Benchmark Issue Backlog

## Context

This backlog summarizes issues observed after running the current fixture-mode benchmark:

```bash
backend/.venv/bin/python -m tests.evaluation.benchmark_runner \
  --suites temporal_freshness,contradiction,insufficient_evidence \
  --variants naive_dense_only,standard_hybrid,standard_no_rerank,enterprise_temporal_rag,enterprise_temporal_no_freshness \
  --output reports/benchmark-current
```

The benchmark was fixture-based, so it does not measure live database retrieval,
vector search, reranker latency, provider latency, token usage, or real Enterprise
branch behavior yet.

## Summary Of Observed Results

| Variant | RAGAS | Recall@5 | Faithfulness | Citation Accuracy | Temporal Accuracy |
|---|---:|---:|---:|---:|---:|
| `naive_dense_only` | 0.701 | 0.750 | 0.613 | 0.458 | 0.250 |
| `standard_hybrid` | 0.638 | 0.750 | 0.613 | 0.708 | 0.250 |
| `standard_no_rerank` | 0.701 | 0.750 | 0.613 | 0.458 | 0.250 |
| `enterprise_temporal_rag` | 0.638 | 0.750 | 0.613 | 0.875 | 0.750 |
| `enterprise_temporal_no_freshness` | 0.638 | 0.750 | 0.613 | 0.708 | 0.250 |

## Issue List

### BENCH-001: Benchmark Is Still Fixture-Mode Only

Priority: High  
Type: Benchmark Infrastructure  
Status: Open

Problem:

The current benchmark run uses deterministic fixture replay. It validates the
benchmark harness, but it does not measure the real Standard or Enterprise system.

Impact:

- Latency is reported as `0ms`.
- Token and cost metrics are `0`.
- Real retrieval, reranking, generation, and trace persistence are not measured.
- Enterprise branch performance cannot be trusted from this run alone.

Suggested fix:

- Run live variants against a seeded database and vector store.
- Add `standard_hybrid_live` and future `enterprise_live` runs to the report.
- Persist live benchmark reports separately from fixture reports.

Acceptance criteria:

- Benchmark report includes non-zero stage latencies.
- Benchmark report includes real retrieved chunk IDs from `QueryTrace`.
- Live Standard results can be compared against fixture replay results.

---

### BENCH-002: Enterprise Branches Are Not Yet Benchmarked With The Shared Harness

Priority: High  
Type: Cross-Branch Benchmarking  
Status: Open

Problem:

Enterprise work exists on branches such as `origin/feat/enterprise-tier-formation`,
but the current benchmark was run only on the current branch.

Impact:

- We cannot yet compare current Standard behavior against the real Enterprise implementation.
- Enterprise temporal scoring, reranking, and query decomposition are not measured by the shared report.
- Branch-level regressions or improvements are unknown.

Suggested fix:

- Use git worktrees for isolated branch benchmarks.
- Overlay or port the benchmark harness into each enterprise branch.
- Run branch-native tests such as `tests/evaluation/test_enterprise_benchmarks.py`.
- Produce one report directory per branch.

Acceptance criteria:

- `reports/benchmark-current/` exists.
- `reports/benchmark-enterprise-foundation/` exists.
- `reports/benchmark-enterprise-formation/` exists.
- Reports use the same summary schema.

---

### BENCH-003: Recall@5 Is Below Target

Priority: High  
Type: Retrieval Quality  
Status: Open

Observed:

`Recall@5 = 0.750`

Target from plan:

`Recall@5 >= 0.80`

Problem:

The benchmark did not retrieve enough required evidence across all cases.

Possible causes:

- Candidate fixture set is too small or not representative.
- Retrieval ranking does not reliably surface all relevant chunks.
- Evidence packaging may remove useful evidence too aggressively.
- Insufficient-evidence cases have no ground truth chunks, which can depress aggregate recall.

Suggested fix:

- Split recall reporting by suite.
- Exclude abstention-only cases from retrieval recall aggregates or report them separately.
- Add more multi-hop and temporal cases with explicit required evidence sets.
- Tune retrieval and evidence selection separately.

Acceptance criteria:

- Suite-level recall is reported.
- Retrieval suites meet `Recall@5 >= 0.80`.
- Abstention suites are measured using abstention correctness instead of recall alone.

---

### BENCH-004: Faithfulness Is Below Target

Priority: High  
Type: Answer Quality  
Status: Open

Observed:

`Faithfulness = 0.613`

Target from plan:

`Faithfulness >= 0.85`

Problem:

Generated fixture answers include terms that are not always directly supported by
the retrieved context under the current heuristic scorer.

Possible causes:

- The fixture answer composer injects expected answers instead of extracting only from evidence.
- The heuristic faithfulness metric is too crude for some wording differences.
- Retrieved context contains stale or irrelevant chunks mixed with relevant chunks.
- Contradiction handling produces long answers that the heuristic scorer penalizes.

Suggested fix:

- Add explicit supported-claim extraction per benchmark case.
- Use `ground_truth_statements` for deterministic claim support scoring.
- Separate fixture answer quality from live generator answer quality.
- Add optional real RAGAS/DeepEval judge mode later.

Acceptance criteria:

- Faithfulness is calculated against statements, not only word overlap.
- Contradiction answers are scored with conflict-aware rules.
- Faithfulness target is evaluated separately for fixture and live modes.

---

### BENCH-005: Temporal Accuracy Improved But Still Below Target

Priority: Medium  
Type: Temporal RAG  
Status: Open

Observed:

`enterprise_temporal_rag temporal_accuracy = 0.750`

Target from plan:

`Temporal Accuracy >= 0.80`

Problem:

The temporal fixture variant improves freshness selection, but still misses the
target threshold.

Possible causes:

- Temporal metric is averaged across non-temporal suites.
- Some cases include fresh evidence but still retain irrelevant non-stale evidence.
- The fixture temporal selector removes stale chunks but does not always optimize for support completeness.

Suggested fix:

- Report temporal accuracy only for `temporal_freshness` cases.
- Add `fresh_evidence_precision` and `stale_evidence_rate` to the Markdown report.
- Ensure temporal evidence packaging removes stale chunks and irrelevant chunks.

Acceptance criteria:

- Temporal suite-only accuracy is reported.
- `enterprise_temporal_rag` reaches `>= 0.80` on temporal cases.
- Stale evidence rate is lower than non-temporal variants.

---

### BENCH-006: Naive Variant Appears Better Than Standard On RAGAS

Priority: Medium  
Type: Benchmark Calibration  
Status: Open

Observed:

`naive_dense_only RAGAS = 0.701`  
`standard_hybrid RAGAS = 0.638`

Problem:

The fixture replay generator gives Naive higher answer relevancy, so Naive appears
better on aggregate RAGAS despite worse citation accuracy and temporal accuracy.

Impact:

- The headline table can be misleading.
- RAGAS is overweighting answer wording in fixture mode.
- Component contribution rows may recommend reviewing useful components.

Suggested fix:

- Separate retrieval/evidence metrics from generated-answer metrics.
- Add a weighted benchmark score that prioritizes citation accuracy, temporal accuracy, and abstention correctness for these suites.
- Do not use fixture-mode RAGAS as the main quality score.

Acceptance criteria:

- Report includes `retrieval_score`, `answer_score`, and `trust_score` separately.
- Fixture-mode report includes a disclaimer about synthetic answer composition.
- Naive is not ranked as better when trust metrics are worse.

---

### BENCH-007: Reranking Ablation Looks Worse Than No Reranking

Priority: Medium  
Type: Ablation Calibration  
Status: Open

Observed:

Component contribution reports:

`Reranking quality_gain = -0.062`

Problem:

The fixture-mode reranking simulation does not reflect the real reranker and may
penalize Standard behavior incorrectly.

Possible causes:

- The simulated reranker changes answer relevancy but not enough citation/trust weighting.
- RAGAS scoring is not aligned with intended trust outcomes.
- The fixture replay path does not model actual Enterprise reranker behavior.

Suggested fix:

- Rename fixture ablations as simulated ablations.
- Add live ablation support only where the real system exposes toggles.
- Compare reranking on real Enterprise branch tests.

Acceptance criteria:

- Report distinguishes `fixture_ablation` from `live_ablation`.
- Real reranker benchmarks run on enterprise branch.
- Reranker contribution is measured on retrieval and evidence metrics separately.

---

### BENCH-008: Insufficient-Evidence Cases Depress Retrieval Metrics

Priority: Medium  
Type: Metric Design  
Status: Open

Problem:

Insufficient-evidence cases intentionally have no relevant chunks, but they are
included in aggregate retrieval metrics.

Impact:

- `Recall@5` and `MRR` look worse even when abstention behavior is correct.
- The main failure is reported as `low_recall` for insufficient-evidence cases.

Suggested fix:

- Separate retrieval benchmarks from abstention benchmarks.
- For `expected_behavior = abstain`, prioritize `abstention_correctness`,
  `unsupported_claim_rate`, and `citation_accuracy`.

Acceptance criteria:

- Insufficient-evidence cases no longer dominate retrieval failure summaries.
- Report has a dedicated abstention section.
- Correct abstention is treated as success.

---

### BENCH-009: Contradiction Handling Needs Conflict-Aware Metrics

Priority: Medium  
Type: Trust And Verification  
Status: Open

Problem:

Contradiction cases need different scoring than direct fact lookup. The system
should be rewarded for surfacing conflicting evidence rather than providing one
flattened answer.

Impact:

- Faithfulness and answer relevancy may understate good conflict behavior.
- Reports do not currently expose a `conflict_handling_score`.

Suggested fix:

- Implement `conflict_handling_score`.
- Use `expected_behavior = surface_conflict` to check that both sides are cited.
- Penalize answers that cite only one side of a known conflict.

Acceptance criteria:

- Contradiction suite reports `conflict_handling_score`.
- Correct conflict disclosure is treated as success.
- Single-sided conflict answers are flagged.

---

### BENCH-010: Pass/Fail Gates Are Not Enforced Yet

Priority: Medium  
Type: Regression Safety  
Status: Open

Problem:

The plan defines gates, but the benchmark runner currently only writes reports.
It does not fail the command when thresholds are missed.

Impact:

- CI cannot block regressions automatically.
- Benchmark failures require manual inspection.

Suggested fix:

- Add `--fail-on-gate` CLI option.
- Add configurable threshold file.
- Return non-zero exit code when gate checks fail.

Acceptance criteria:

- Benchmark can run in report-only mode.
- Benchmark can run in CI gate mode.
- Gate failures are listed clearly in the Markdown report.

---

### BENCH-011: Benchmark Fixture Coverage Is Still Too Small

Priority: Medium  
Type: Dataset Coverage  
Status: Open

Problem:

Current new fixture coverage includes temporal, contradiction, and insufficient
evidence cases only. The plan also calls for basic lookup, field extraction,
list collection, comparison, multi-hop, conversation follow-up, and source policy.

Impact:

- Benchmark conclusions are too narrow.
- Enterprise behavior on multi-hop and query decomposition is under-tested.

Suggested fix:

- Add the remaining fixture suites.
- Include at least 10-20 cases per suite initially.
- Expand to larger benchmark sets after the harness stabilizes.

Acceptance criteria:

- All planned suites exist as fixtures.
- Each suite has documented expected behavior.
- Summary report includes suite-level metrics.

---

### BENCH-012: Live Enterprise Variant Is Missing

Priority: High  
Type: Enterprise Benchmarking  
Status: Open

Problem:

The current harness has fixture `enterprise_temporal_rag`, but not a real live
Enterprise variant wired to `ExecutionTier.ENTERPRISE` from the enterprise branch.

Impact:

- Real enterprise temporal scoring, reranking, query decomposition, and evidence
  packaging are not measured by the shared benchmark.

Suggested fix:

- Add `enterprise_live` after integrating or benchmarking the enterprise branch.
- Add live ablations for temporal scoring, reranker, and query decomposition if
  the branch exposes safe flags.

Acceptance criteria:

- `enterprise_live` appears in benchmark reports.
- Enterprise live report includes non-zero latency and real trace data.
- Enterprise live can be compared to `standard_hybrid_live`.

## Suggested Jira/Trello Columns

Use these columns if this backlog is imported into a board:

| Column | Meaning |
|---|---|
| Backlog | Issue captured but not started |
| Ready | Clear acceptance criteria and owner |
| In Progress | Actively being worked on |
| In Review | Code/review/benchmark output ready |
| Done | Acceptance criteria met |

## Suggested Jira Fields

| Field | Suggested Value |
|---|---|
| Project | Grounded Benchmarking |
| Issue Type | Task or Bug |
| Component | Benchmark, Retrieval, Temporal RAG, Enterprise, Metrics |
| Priority | High, Medium, Low |
| Labels | `benchmark`, `rag`, `enterprise`, `temporal`, `quality`, `latency` |
| Epic | RAG Benchmark And Performance Optimization |

## Suggested Next Actions

1. Create board tickets from `BENCH-001` through `BENCH-012`.
2. Start with `BENCH-001`, `BENCH-002`, `BENCH-003`, `BENCH-004`, and `BENCH-012`.
3. Keep fixture-mode and live-mode results separate.
4. Add pass/fail gates only after metric calibration issues are addressed.
5. Use worktrees to benchmark enterprise branches without disturbing the current branch.
