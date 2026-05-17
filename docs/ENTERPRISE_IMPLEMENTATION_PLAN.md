# Enterprise Tier Implementation Plan

**Status:** implemented on the current branch, with rollout hardening ongoing  
**Updated:** 2026-04-21

## Purpose

Build the **Enterprise** tier of the RAG system as the next level above Standard.

Enterprise should deliver:

- stronger retrieval precision on hard questions
- better evidence quality before generation
- measurable uplift over Standard
- explainable routing and tracing
- controlled latency/cost tradeoffs

Enterprise should be **deeper, not messier**.

---

## Tier Boundaries

### Standard

Fast, stable grounded baseline:

- hybrid retrieval
- lightweight query planning
- current evidence packaging
- citations / grounding
- predictable latency

### Enterprise

Higher capability for hard retrieval cases:

- model-based reranking
- hard-query routing
- deeper query planning
- stronger evidence packaging
- temporal/freshness-aware ranking
- richer tracing/debugging
- benchmark-proven uplift

### Critical

Highest-assurance mode:

- verifier / critic loops
- corrective retrieval
- strict answer acceptance
- high-confidence policy enforcement

---

## Engineering Principles

- Standard must remain stable.
- Enterprise logic should be clearly separated.
- Benchmark before rollout.
- Prefer explicit interfaces over hidden heuristics.
- Keep latency/cost measurable.
- Favor maintainable code over clever code.
- Add observability early.

---

## Current Implementation Snapshot

The current branch now includes:

- Enterprise tier scaffolding
- explicit Enterprise routing from `Thinking`
- explainable Auto-to-Enterprise routing for hard queries
- deeper query planning
- controlled query decomposition
- temporal scoring
- stronger Enterprise evidence packaging
- reranker abstraction and Gemini-backed reranker implementation
- Enterprise benchmark coverage
- richer retrieval and evidence trace/debug metadata
- frontend capability wiring for live `Thinking` mode

Still intentionally not live:

- `Verified`
- Critical verifier loops
- semantic chunking as the default

Current live Enterprise behavior:

- `Thinking` is enabled and routes directly to Enterprise
- `Auto` can route eligible hard queries into Enterprise
- Enterprise reranking is enabled by default with disabled-safe fallback behavior
- `Verified` remains out of scope for this plan

---

## Recommended Build Order

1. Freeze Standard baseline
2. Add Enterprise scaffolding
3. Add reranker interface
4. Implement model-based reranker
5. Add minimal hard-query routing
6. Improve Enterprise evidence packaging
7. Add deeper query planning
8. Add temporal scoring
9. Add controlled query decomposition
10. Expand benchmarks
11. Improve trace/debug visibility
12. Enable Thinking mode

---

## Phase-by-Phase Plan

## Phase 1 - Enterprise Scaffolding

### Goal
Create the execution boundary with no quality changes.

### Tasks

- add `ExecutionTier.ENTERPRISE`
- add config flags
- add request-level routing hooks
- add tier-aware telemetry
- add trace metadata

### Likely Files

- `backend/app/config.py`
- `backend/app/services/query.py`
- routing / telemetry modules

### Success Criteria

- Enterprise can be explicitly invoked
- traces show Standard vs Enterprise
- no behavior change when Enterprise is disabled

### Status

- implemented

---

## Phase 2 - Reranker Interface

### Goal
Create a clean abstraction before choosing a backend.

### Tasks

- define reranker interface
- input: query + retrieved chunks
- output: reordered chunks + scores + debug info
- disabled-safe fallback path

### Likely Files

- `backend/app/core/reranker.py`
- `backend/app/services/retrieval.py`

### Success Criteria

- retrieval works with reranker off
- retrieval works with stub reranker on
- no duplication across tiers

### Status

- implemented

---

## Phase 3 - Model-Based Reranking

### Goal
Improve ranking precision on hard queries.

### Tasks

- rerank top 20-30 fused candidates
- integrate real model backend
- preserve tenant / namespace isolation
- log reranker scores

### Success Criteria

- top-k retrieval uplift on hard queries
- fewer noisy chunks reach evidence layer
- Enterprise beats Standard on benchmarked difficult cases

### Current rollout state

- implemented
- enabled by default for Enterprise
- uses Gemini when credentials are available
- falls back safely to fused ordering when the reranker backend is unavailable

---

## Phase 4 - Minimal Hard-Query Routing

### Goal
Use Enterprise only when needed.

### Route to Enterprise When

- multi-part questions
- comparison-heavy questions
- ambiguous queries
- weak Standard retrieval confidence
- retrieval-hostile wording

### Success Criteria

- easy queries stay in Standard
- hard queries route to Enterprise
- latency remains controlled

### Status

- implemented

---

## Phase 5 - Enterprise Evidence Packaging

### Goal
Provide cleaner evidence for difficult questions.

### Tasks

- stronger comparison bundles
- better multi-section packaging
- better multi-part exact support
- richer but compact evidence sets

### Likely Files

- `backend/app/services/evidence.py`

### Success Criteria

- comparison answers improve
- multi-part answers improve
- evidence richer without excess noise

### Status

- implemented

---

## Phase 6 - Deeper Query Planning

### Goal
Improve recall and precision for complex questions.

### Tasks

- classify hard queries more precisely
- decide when one retrieval pass is enough
- decide when multiple retrieval intents are needed
- add controlled rewrite expansion

### Do Not Add Yet

- aggressive decomposition everywhere
- recursive retrieval loops
- fully agentic planning

### Success Criteria

- complex question performance improves
- no large increase in noise
- rewrite drift remains controlled

### Status

- implemented

---

## Phase 7 - Temporal / Freshness Scoring

### Goal
Prefer newer evidence when recency matters.

### Tasks

- selective freshness boosts
- support versioned docs / policies / product docs
- balance relevance vs recency

### Success Criteria

- version-sensitive queries improve
- older relevant docs still win when appropriate

### Status

- implemented

---

## Phase 8 - Controlled Query Decomposition

### Goal
Break retrieval-hostile queries into manageable intents.

### Use Cases

- multi-part questions
- complex comparisons
- hard follow-ups
- compound intents

### Success Criteria

- compound queries improve
- decomposition helps more than hurts
- acceptable latency

### Status

- implemented

---

## Phase 9 - Enterprise Evaluation Expansion

### Goal
Prove Enterprise uplift.

### Benchmark Categories

- hard exact lookup
- multi-part questions
- comparison questions
- recency-sensitive questions
- ambiguous follow-ups
- retrieval-hostile wording
- policy / product docs

### Metrics

- retrieval hit rate
- evidence sufficiency
- answer correctness
- citation correctness
- latency
- cost

### Status

- implemented

---

## Phase 10 - Trace / Debug Visibility

### Goal
Make Enterprise inspectable end-to-end.

### Expose

- whether Enterprise was used
- why it was chosen
- reranker usage
- reranker top results
- selected evidence package
- planning decisions

### Success Criteria

- one run can be debugged end-to-end

### Status

- implemented

---

## Phase 11 - Thinking Mode Enablement

### Goal
Expose advanced mode only after real quality gains exist.

### Thinking Mode Must Reflect

- reranking
- deeper planning
- stronger evidence handling

### Success Criteria

- measurable hard-query uplift
- explainable behavior
- stable latency envelope

### Current rollout state

- implemented
- enabled in backend capabilities
- exposed in the frontend product shell
- backed by Enterprise execution and trace metadata

---

## What Belongs in Enterprise

- model-based reranker
- hard-query routing
- deeper query planning
- controlled rewrites
- stronger evidence packaging
- temporal scoring
- richer traces
- benchmarked uplift

---

## What Should Stay in Critical

- verifier / critic loops
- corrective retrieval loops
- strict acceptance policies
- claim-by-claim verification
- highest-assurance answering

---

## Rollout Guidance

1. Ship behind feature flags.
2. Compare against Standard continuously.
3. Roll out gradually.
4. Revert quickly if regressions appear.
5. Keep Standard fast and dependable.

## Current rollout notes

- Standard remains the default low-latency path
- Enterprise is live for `Thinking` and eligible Auto routes
- reranker rollout is enabled, but still depends on Gemini provider availability for full model-based uplift
- the next validation focus is broader manual smoke testing and benchmark comparison under real provider conditions

---

## Final Rule

**Enterprise should feel smarter because it is better engineered, not because it is noisier.**
