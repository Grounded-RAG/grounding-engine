# Phase 2 Enterprise Plan

**Status:** live backend path, rollout hardening in progress  
**Date:** 2026-04-21  
**Prerequisite:** Phase 1 Standard backend and Phase 1.5 product-shell backend are complete

## Purpose

This document defines exactly what **Phase 2** means for Grounded.

Phase 2 is the **Enterprise tier**.

Its job is to improve retrieval precision and evidence quality without
destabilizing the strong Standard baseline that already exists today.

Phase 2 is where Grounded turns on the real backend path behind:

- `Thinking`

It is **not** the phase for uncontrolled web fallback, unrestricted model
knowledge, or high-assurance critic loops. Those belong later in Phase 3.

---

## 1. What Was Already Live Before Phase 2

Before Phase 2 started, the platform already had:

- Phase 1 Standard ingestion and query
- hybrid sparse + dense retrieval
- deterministic chunking
- evidence packaging
- grounded generation
- structured citations
- degraded responses
- trace persistence
- Phase 1.5 product-shell backend:
  - workspaces
  - datasets
  - agents
  - conversations
  - messages
  - run history
  - dashboard APIs
  - API key management
  - user-facing mode contract

Current live mode behavior:

- `Auto` -> Standard by default, with Enterprise auto-routing on eligible hard queries
- `Instant` -> Standard
- `Thinking` -> enabled and backed by Enterprise
- `Verified` -> visible but disabled

So Phase 2 did **not** start from zero.
It started from a working product and a working Standard engine.

Current implementation status:

- Enterprise routing is live
- `Thinking` is enabled in capabilities and the product shell
- Enterprise planning, temporal scoring, controlled decomposition, stronger evidence packaging, and trace metadata are implemented
- Enterprise reranker rollout is enabled by default with a disabled-safe fallback when provider credentials are unavailable
- `Verified` remains intentionally out of scope for Phase 2

---

## 2. What Phase 2 Is Trying To Achieve

Phase 2 should answer this question:

> How do we make Grounded better on harder, more ambiguous, freshness-sensitive,
> and multi-hop document questions without breaking the fast Standard path?

The expected Enterprise uplift is:

- better recall for hard queries
- better precision in the top retrieved candidates
- better evidence selection before answer generation
- stronger routing decisions for when deeper retrieval is worth the latency

In product terms:

- `Thinking` becomes real
- `Auto` can recommend or route into Enterprise when appropriate
- users get better answers for hard questions, not just slower answers

---

## 3. What Phase 2 Includes

Phase 2 includes these capabilities. The list below reflects the current live
implementation unless explicitly marked as experimental or still gated.

### 3.1 Planner for eligible queries

This adds controlled query planning and transformation for questions that are
too vague, multi-part, or retrieval-hostile for the Standard path.

Examples of queries that should become eligible:

- comparison questions
- multi-hop questions
- freshness-sensitive questions
- broad policy interpretation questions
- ambiguous questions that need rewriting or expansion

Planner responsibilities may include:

- query rewrite
- query expansion
- multi-query decomposition
- early-exit logic for obviously simple queries
- reasoning about whether Enterprise depth is warranted

Important rule:

- do **not** run the planner on every simple query
- Enterprise should be deeper, not wasteful

### 3.2 Temporal and freshness scoring

This adds recency awareness when the domain or dataset policy makes freshness
important.

Examples:

- policies with recent revisions
- operational documents with changing procedures
- regulatory material where newer evidence should win

Expected behavior:

- newer evidence can outrank older evidence when the query or dataset profile
  demands it
- older evidence should still win when it is clearly more relevant

Important rule:

- freshness must be a **scoring signal**, not a blind override

### 3.3 Reranking

This adds a second-stage scoring pass after initial retrieval.

The first pass still returns candidates from:

- sparse retrieval
- dense retrieval
- RRF fusion

Reranking then improves the final shortlist by rescoring the most promising
candidates.

Expected outcome:

- fewer near-miss chunks
- fewer duplicated or weak candidates
- stronger evidence packages before generation

Current live rollout:

- Enterprise reranking is enabled by default
- Gemini is the default provider-backed reranker backend
- if Gemini credentials are unavailable, Enterprise stays live and falls back to fused retrieval ordering with traceable reranker debug metadata

### 3.4 Stronger evidence packaging

Standard already packages evidence.

Enterprise improves the quality of the final evidence package by using:

- better candidate selection
- better deduplication
- better freshness-aware ordering
- stronger support for multi-part questions

This is important because even a strong generator can only be as good as the
evidence it receives.

### 3.5 Semantic chunking experiment

Phase 2 is the first phase where semantic chunking may be introduced, but only
behind flags and evaluation.

This should be treated as a controlled experiment, not an unconditional default.

Expected approach:

- keep deterministic chunking as the baseline
- add semantic chunking behind configuration or feature flags
- compare it against deterministic chunking on retrieval and answer metrics
- keep it disabled if it does not clearly improve results

Important rule:

- semantic chunking is a **candidate upgrade path**
- it is not automatically the new default

Current state:

- semantic chunking is not live as the Enterprise default
- deterministic chunking remains the active baseline

### 3.6 Enterprise routing policies

Phase 2 introduces clearer rules for when a query belongs in Enterprise.

Possible reasons:

- query ambiguity
- high complexity
- temporal sensitivity
- weak Standard candidate quality
- multi-hop retrieval need

This logic influences:

- `Auto` mode routing
- `Thinking` mode execution
- trace metadata and user-facing explanations

---

## 4. What Phase 2 Does Not Include

Phase 2 should **not** include:

- uncontrolled web fallback
- Corrective RAG with external retrieval
- Internal Model Retrieval as a normal path
- high-assurance critic / verifier loop
- unrestricted general-knowledge answering
- silent mixing of grounded and ungrounded sources

Those belong to **Phase 3 Critical**.

This separation matters because Enterprise is about **retrieval precision**,
while Critical is about **highest-assurance verification**.

---

## 5. Product Meaning Of Enterprise

Enterprise is the backend path behind:

- `Thinking`

### Product promise

`Thinking` should mean:

- deeper retrieval
- better ranking
- better evidence selection
- slightly more latency
- stronger performance on hard document questions

### Product promise it should not make

It should **not** promise:

- live web research
- unrestricted model knowledge fallback
- legal-grade verification
- critical review workflows

Those promises belong later.

---

## 6. Runtime Model In Phase 2

### User-facing modes

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

### Internal execution tiers

- `Standard`
- `Enterprise`
- `Critical`

### Phase 2 runtime behavior

| User-facing mode | Phase 2 backend behavior |
|---|---|
| `auto` | route to Standard or Enterprise depending on eligibility |
| `instant` | route to Standard |
| `thinking` | route to Enterprise |
| `verified` | still disabled or coming soon |

### Important routing rule

The system should still respect:

- dataset minimum tier
- tenant entitlement
- plan limits
- dataset safety rules
- routing logic for query complexity

The system must never silently run below the safe tier floor.

---

## 7. Recommended Architecture Changes

### 7.1 Planner module

Add a dedicated service responsible for:

- deciding whether planning is needed
- transforming eligible queries
- recording planner output in trace metadata

Recommended outputs:

- original query
- rewritten query
- optional subqueries
- planning applied flag
- planning rationale

### 7.2 Retrieval scoring upgrades

Keep the current retrieval backbone:

- sparse retrieval
- dense retrieval
- RRF fusion

Then add Enterprise-only scoring stages:

- temporal scoring
- reranking

Recommended order:

1. candidate retrieval
2. fusion
3. temporal scoring adjustment
4. reranking
5. final evidence selection

### 7.3 Trace and run metadata expansion

Enterprise should record richer trace details such as:

- whether planning was applied
- rewritten query text or plan summary
- whether temporal scoring was applied
- whether reranking was applied
- scoring/routing rationale
- final Enterprise activation reason

This is important so the system stays inspectable even as it becomes smarter.

Current trace status:

- Enterprise routing reasons are persisted
- retrieval debug metadata is persisted
- evidence debug metadata is persisted
- reranker and freshness debug details are available in run traces

### 7.4 Evaluation hooks

Phase 2 should add evaluation hooks around:

- planner effectiveness
- reranker uplift
- semantic chunking uplift
- temporal scoring uplift
- latency cost

This should be measurable before Enterprise is broadly enabled.

---

## 8. Data And API Impact

Phase 2 should prefer evolving the current APIs over inventing a parallel API
surface.

### Endpoints that should stay stable

- `POST /v1/query`
- `POST /v1/agents/{agent_id}/chat`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/capabilities`

### What changes in the behavior

- `Thinking` is enabled in capabilities
- `Auto` may route some queries to Enterprise
- `runs` expose richer routing metadata
- route explanations are more informative

### Suggested trace / run additions

Potential fields to add:

- `planning_applied`
- `planning_reason`
- `temporal_scoring_applied`
- `reranker_applied`
- `chunking_strategy_used`
- `enterprise_activation_reason`

These should be added only if they make trace inspection better and remain easy
to reason about.

---

## 9. Suggested Build Order

The cleanest Phase 2 order was:

1. planner eligibility rules and query transformation service
2. trace fields for planning and Enterprise routing
3. temporal scoring
4. reranker
5. stronger evidence selection logic
6. semantic chunking experiment behind flags
7. capabilities update to enable `thinking`
8. Auto routing rules for Enterprise eligibility
9. evaluation and benchmark pass

This order kept the changes measurable and reduced the risk of shipping too
many interacting retrieval changes at once.

---

## 10. Testing Strategy

Phase 2 needs stronger testing than Phase 1 because the behavior is no longer
just "does retrieval work?" but also "did the deeper path actually help?"

### Unit tests

Add unit tests for:

- planner eligibility logic
- query rewrite behavior
- temporal score calculations
- reranker selection behavior
- Enterprise routing decisions

### Integration tests

Add integration tests for:

- `Thinking` mode request path
- `Auto` routing into Enterprise
- trace metadata on Enterprise runs
- dataset policies that require Enterprise
- Enterprise fallback to Standard when not eligible

### Evaluation tests

Measure:

- precision@k
- recall@k
- nDCG@k
- answer faithfulness
- citation validity
- latency impact

### Manual / Swagger validation

Phase 2 Swagger checks should extend the current Phase 1.5 flow with:

- `GET /v1/capabilities` showing `thinking` enabled
- `POST /v1/agents/{agent_id}/chat` with `mode = "thinking"`
- `POST /v1/query` or agent chat using hard ambiguous questions
- `GET /v1/runs/{run_id}` showing Enterprise routing metadata

---

## 11. Definition Of Done

Phase 2 is complete when:

1. `Thinking` is truly enabled and backed by the Enterprise path
2. Enterprise measurably improves hard-query retrieval quality over Standard
3. planner, temporal scoring, and reranking are all traceable and test-covered
4. semantic chunking remains gated unless it wins on evaluation
5. `Auto` can route eligible queries into Enterprise correctly
6. Enterprise does not quietly include Critical-only behavior
7. run history and trace inspection stay clear and understandable

Current completion note:

- the Enterprise path itself is now live
- the remaining work is rollout validation, broader manual smoke testing, and optional experiments such as semantic chunking

---

## 12. Clear Boundary With Phase 3

Phase 2 should stop at:

- retrieval precision
- stronger evidence quality
- smarter routing into Enterprise

Phase 3 begins when the platform adds:

- verifier / critic loop
- corrective retrieval
- allowlisted web fallback
- Internal Model Retrieval
- highest-assurance workflows

That boundary should stay clean.

---

## 13. One-Sentence Summary

Phase 2 makes Grounded better at **finding the right evidence for hard
questions**, and it turns `Thinking` into a real Enterprise retrieval path
without blurring the line into Phase 3 verification features.
