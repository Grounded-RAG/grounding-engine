# Grounded Implementation Plan

**Status:** Architecture-aligned revision  
**Date:** 2026-03-21  
**Prerequisite:** `SYSTEM_DESIGN.md`

## 1. Planning Defaults

Use these defaults unless the team makes an explicit architecture decision to
change them:

- sparse v1: PostgreSQL FTS
- dense v1: Qdrant
- default chunking: deterministic token-aware chunking
- semantic chunking: later than deterministic chunking
- planner: Enterprise and Critical by default
- reranker: Enterprise and Critical
- web fallback: Critical only
- internal model retrieval: Critical only
- UX default: Auto (Recommended)
- user-facing subscription plans:
  - Free Plan
  - Pro Plan
  - Business Plan
  - Enterprise Plan

## 2. Delivery Strategy

### Phase 0 - Foundations and Safety

**Goal:** make the backend safe to build on.

Includes:

- repo bootstrap
- local setup
- health endpoints
- environment validation
- database wiring and migrations
- tenant, namespace, API key, document, ingestion job, and trace models
- auth and tenant resolution
- object storage integration
- structured logging and telemetry
- baseline tests and CI

Excluded:

- retrieval features
- ingestion workflow
- query answering

Exit criteria:

- health endpoints work
- migrations run cleanly
- tenant-scoped requests are enforced
- object storage works locally
- basic CI checks run

Why it belongs here:

- everything later depends on auth, schema, storage, and observability

### Phase 0.5 - Architecture Alignment and Audit

**Goal:** finalize the docs and verify the backend foundation against the final
architecture.

Includes:

- solution architecture doc
- team brief
- rewritten system design
- rewritten implementation plan
- rewritten engineering guardrails
- README alignment
- proposal and ARP alignment notes
- audit of Phase 0 against the new plan/tier/routing model

Excluded:

- new user-facing backend features

Exit criteria:

- docs use one vocabulary
- plans and tiers are clearly separated
- Phase 0 alignment fixes are complete
- any required foundation follow-ups are identified

Why it belongs here:

- Phase 1 should not begin on top of contradictory architecture documents

### Phase 1 - Standard Tier

**Goal:** ship a narrow, strong, production-grade baseline RAG path.

Included capabilities:

- upload and ingestion job creation
- text extraction
- metadata enrichment
- deterministic chunking
- dense indexing in Qdrant
- sparse indexing in PostgreSQL FTS
- hybrid retrieval with RRF
- evidence packaging and citation mapping
- grounded generation
- structured citation schema
- degraded response behavior
- trace persistence
- Standard query APIs

Explicitly excluded:

- planner by default
- semantic chunking default
- reranker
- CRAG
- internal model retrieval
- critic loop

Exit criteria:

- Standard tier returns grounded answers with citations
- uploads are async and job status is visible
- tenant isolation is enforced in dense and sparse retrieval
- traces record `tier_used` and degraded reasons
- baseline evaluation exists

Evaluation criteria:

- faithfulness and citation validity are measured
- Standard is measurably stronger than a naive baseline

Why it belongs here:

- this is the first usable product slice
- it proves the platform can ingest, retrieve, and answer safely

### Phase 2 - Enterprise Tier

**Goal:** improve retrieval precision without destabilizing the Standard path.

Included capabilities:

- planner for eligible queries
- temporal and freshness scoring
- reranking
- stronger evidence packaging
- semantic chunking experiment behind flags and evaluation
- Enterprise routing policies
- Enterprise-tier integration tests and benchmarks

Explicitly excluded:

- web fallback
- internal model retrieval as a normal path
- full critic loop

Exit criteria:

- Enterprise improves precision over Standard or stays disabled
- planner, reranking, and temporal scoring are all measurable
- semantic chunking remains gated unless it wins on evaluation

Evaluation criteria:

- precision@k
- recall@k
- nDCG@k
- answer faithfulness
- latency impact by tier

Why it belongs here:

- these are quality uplift features, not baseline requirements

### Phase 3 - Critical Tier

**Goal:** add the highest-assurance path for difficult and high-risk queries.

Included capabilities:

- verification / critic loop
- Corrective RAG with allowlisted web fallback
- Internal Model Retrieval
- FreshPrompt conflict-resolution behavior
- strict unsupported-claim handling
- async verified query path
- Critical policy tests and drills

Explicitly excluded:

- uncontrolled web search
- silent downgrade below required safety level

Exit criteria:

- Critical path works with bounded retries
- web fallback is policy-controlled and observable
- async verified query path is available
- verifier outcomes are traceable

Evaluation criteria:

- unsupported-claim reduction
- verifier rejection rate
- web-fallback activation rate
- high-risk scenario test coverage

Why it belongs here:

- these are highest-latency, highest-complexity assurance features

## 3. Capability Placement Summary

| Capability | Phase |
|---|---|
| Metadata enrichment | Phase 1 |
| Deterministic chunking | Phase 1 |
| Semantic chunking | Phase 2 |
| Namespace isolation | Phase 0 |
| Query planning and transformation | Phase 2 |
| Hybrid retrieval with RRF | Phase 1 |
| Temporal and freshness scoring | Phase 2 |
| Reranking | Phase 2 |
| Internal model retrieval | Phase 3 |
| Corrective RAG | Phase 3 |
| Evidence packaging and citation mapping | Phase 1 |
| Grounded generation | Phase 1 |
| Verification loop | Phase 3 |
| FreshPrompt strategy | Phase 3 |
| Structured citation schema | Phase 1 |
| Degraded response and abstention | Phase 1 |
| Trace, audit, and evaluation | Phase 0 and Phase 1 |

## 4. What We Build First

Use this order now that the Phase 0 alignment fixes are complete:

1. build upload and ingestion job APIs
2. build extraction and metadata enrichment
3. build deterministic chunking
4. build dense and sparse indexing
5. build hybrid retrieval with RRF
6. build evidence packaging
7. build grounded generation and structured citations
8. persist traces and degraded reasons
9. ship Standard query APIs

Only after Standard is stable:

10. add Enterprise planner, temporal scoring, and reranking
11. add Critical verification, corrective retrieval, and internal model retrieval

## 5. Phase 0 Alignment Fixes

Completed before Phase 1 coding starts:

- `Tenant.plan_tier` was split into:
  - `subscription_plan`
  - `max_execution_tier`
- namespace policy fields were added
- traces now expose explicit routing fields
- docs and setup were aligned to the new model

## 6. Definition of Done for Architecture Alignment

The planning layer is ready when:

- docs use one architecture model
- the team understands plans vs tiers
- Phase 1 has a narrow and agreed scope
- excluded capabilities are written down clearly
- no one needs to guess where a feature belongs
