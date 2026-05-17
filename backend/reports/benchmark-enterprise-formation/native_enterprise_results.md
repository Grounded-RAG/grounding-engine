# Enterprise Formation Native Benchmark Results

Branch tested: `origin/feat/enterprise-tier-formation`  
Commit tested: `d42f9eb feat: enable enterprise tier features and update status to live`  
Worktree: `/Users/mac/Desktop/grounding-engine-enterprise-formation`  
Date: 2026-05-02

## Commands

```bash
.venv/bin/python -m pytest tests/evaluation/test_enterprise_benchmarks.py
```

```bash
.venv/bin/python scripts/run_standard_pilot_eval.py
```

## Enterprise Benchmark Tests

Result:

```text
2 passed, 134 warnings in 0.43s
```

Covered assertions:

- Enterprise query planning improves retrieval-query coverage for hard comparison questions.
- Enterprise evidence packaging includes broader evidence for comparison questions.
- Enterprise evidence packaging keeps all required evidence for multi-part questions.
- Enterprise temporal scoring outranks stale evidence for recency-sensitive queries.

Warnings:

- Deprecation warnings from Python 3.14 / FastAPI / pytest-asyncio around `asyncio` APIs.
- No benchmark failure from these warnings.

## Pilot Evaluation

Provider used:

```text
local-grounded-v1
```

Summary:

| # | Query Type | Expected Behavior | Observed Result |
|---:|---|---|---|
| 1 | Date range | Answer start/end dates | Passed |
| 2 | Count | Answer number of vans | Passed |
| 3 | Entity | Answer supplier | Passed |
| 4 | Attribute | Answer battery capacity | Passed |
| 5 | Count/entity | Answer charging stations | Passed |
| 6 | Multi-part | Answer departments and van counts | Passed |
| 7 | Time range | Answer charging hours | Passed |
| 8 | Numeric fact | Answer total kilometers | Passed |
| 9 | Event lookup | Answer April event | Passed |
| 10 | Event lookup | Answer June event | Passed |
| 11 | Feedback summary | Answer staff concern | Passed |
| 12 | List/action | Answer committee recommendations | Passed |
| 13 | Arithmetic | Answer fuel/electricity difference | Passed |
| 14 | Arithmetic | Answer maintenance savings | Passed |
| 15 | Arithmetic | Answer net savings after installation | Passed |
| 16 | Missing fact | Abstain | Passed |
| 17 | Missing fact | Abstain | Passed |
| 18 | Missing fact | Abstain | Passed |

Observed answers matched expected answers semantically for all 18 questions.

## Interpretation

The enterprise formation branch has working branch-native enterprise benchmark
coverage for planning, evidence packaging, and temporal scoring. The pilot eval
also shows strong local grounded behavior on a compact synthetic dataset,
including correct abstention for unsupported questions.

This is not yet a full shared-harness benchmark because the enterprise branch
does not contain the new benchmark runner added on `benchmark/performance-eval-foundation`.
The next step is to either port the shared harness into the enterprise branch or
run it from a neutral harness worktree against branch-specific code.

## Follow-Up Issues

- `BENCH-002`: Enterprise branches still need shared-harness benchmark reports.
- `BENCH-012`: Add a true `enterprise_live` variant using the enterprise runtime path.
- Add a cross-branch comparison table once `benchmark-enterprise-foundation` and
  `benchmark-enterprise-formation` reports use the same schema as `benchmark-current`.
