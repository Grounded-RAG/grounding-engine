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
- user-facing modes:
  - Auto
  - Instant
  - Thinking
  - Verified
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

### Phase 1.5 - Product Shell and Workspace Model

**Goal:** turn the Standard backend into a clear product shell built around
datasets, agents, chats, and user-facing modes.

Included capabilities:

- product object model:
  - organization
  - workspace
  - dataset
  - agent
  - conversation
  - run
- dataset management APIs and views
- document listing and ingestion monitoring for datasets
- agent creation and update APIs
- conversation and message persistence
- run history and answer inspection views
- user-facing mode selector:
  - Auto
  - Instant
  - Thinking
  - Verified
- mapping from user-facing modes to internal execution tiers
- usage and entitlement display by plan

Explicitly excluded:

- Enterprise retrieval upgrades themselves
- Critical verification features
- uncontrolled workflow automation

Exit criteria:

- users can work through:
  - organization
  - workspace
  - dataset
  - agent
  - chat
- agents can have default modes and attached datasets
- conversations and runs are persisted
- users can inspect answer citations and run metadata

Evaluation criteria:

- product flow is understandable without backend vocabulary
- the app clearly communicates datasets, agents, modes, and answer provenance

Why it belongs here:

- the Standard backend exists, but the full product shell still needs to be
  layered on top of it before the system feels complete to end users
- this phase should happen before or alongside deeper Enterprise work so the UX
  does not outrun the product model

Detailed backend build order for this phase:

- `docs/PHASE_1_5_BACKEND_PLAN.md`

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

Detailed Phase 2 delivery plan:

- `docs/PHASE_2_ENTERPRISE_PLAN.md`

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

Detailed Phase 3 delivery plan:

- `docs/PHASE_3_CRITICAL_PLAN.md`

### Phase 4 - Adaptive Grounding and Source-Aware Intelligence

**Goal:** expand Grounded beyond strict dataset-only answering without
weakening the trust contract.

Included capabilities:

- grounding policy model:
  - Strict
  - Balanced
  - Live
- pluggable LLM-backed generation layer
- source-aware routing
- explicit model-knowledge augmentation with disclosure
- live or external augmentation with disclosure
- source-aware answer composition
- richer source-disclosure and run metadata

Explicitly excluded:

- hidden source mixing
- vague continuous grounding controls as the main UX model
- unrestricted creative mode inside the same trust contract as grounded work
- bypassing dataset policy or plan entitlement limits

Exit criteria:

- grounding policy is explicit and enforceable
- generator backends are pluggable
- mixed-source answers are clearly disclosed
- grounded and ungrounded sections remain distinguishable
- ambiguity handling improves without weakening trust

Evaluation criteria:

- groundedness
- hallucination rate
- ambiguity-resolution quality
- disclosure accuracy
- answer completeness
- latency and cost impact

Why it belongs here:

- this is where Grounded becomes a source-aware reasoning system rather than
  only a dataset-first RAG platform

Detailed Phase 4 delivery plan:

- `docs/PHASE_4_ADAPTIVE_GROUNDING_PLAN.md`

### Phase 5 - Platform Maturity

**Goal:** make Grounded enterprise-operable at scale across governance,
connectors, operations, and deployment.

Included capabilities:

- connectors and sync
- governance and identity controls
- usage, quota, and billing visibility
- operations and observability tooling
- deployment and security maturity
- evaluation and continuous-improvement operations

Explicitly excluded:

- redefining the core tier model
- weakening trust and disclosure rules

Exit criteria:

- enterprise governance is in place
- connectors and sync are inspectable and reliable
- usage and billing visibility are trustworthy
- operators can run the platform cleanly

Evaluation criteria:

- connector reliability
- access-control coverage
- metering correctness
- operational incident visibility
- deployment smoke coverage

Why it belongs here:

- after the intelligence stack is mature, the platform still needs to become
  operationally complete

Detailed Phase 5 delivery plan:

- `docs/PHASE_5_PLATFORM_MATURITY_PLAN.md`

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
| Grounding policy model | Phase 4 |
| Source-aware routing | Phase 4 |
| Pluggable LLM-backed generation | Phase 4 |
| Mixed-source disclosure | Phase 4 |
| Structured citation schema | Phase 1 |
| Degraded response and abstention | Phase 1 |
| Trace, audit, and evaluation | Phase 0 and Phase 1 |

## 4. Product-Layer Roadmap

| Product capability | Phase |
|---|---|
| Organization / workspace shell | Phase 1.5 |
| Dataset management | Phase 1.5 |
| Agent model | Phase 1.5 |
| Conversation history | Phase 1.5 |
| Run history and answer inspection | Phase 1.5 |
| User-facing mode selector | Phase 1.5 |
| Enterprise retrieval upgrades | Phase 2 |
| Critical verification and corrective behaviors | Phase 3 |
| Adaptive grounding policies | Phase 4 |
| Connectors, governance, and platform operations | Phase 5 |

## 5. What We Build First

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

Now that Standard is stable:

10. keep the product shell aligned with backend contracts:
    - datasets, agents, conversations, runs, and API keys stay stable
    - `Auto` and `Instant` stay live
    - `Thinking` and `Verified` stay honest and clearly unavailable until implemented
11. add Enterprise planner, temporal scoring, reranking, and semantic chunking evaluation
12. activate `thinking` through the Enterprise path only after evaluation wins
13. add Critical verification, corrective retrieval, and internal model retrieval
14. add adaptive grounding policies, source-aware generation, and explicit mixed-source disclosure
15. add connectors, governance, metering, and platform operations maturity

## 6. Phase 0 Alignment Fixes

Completed before Phase 1 coding starts:

- `Tenant.plan_tier` was split into:
  - `subscription_plan`
  - `max_execution_tier`
- namespace policy fields were added
- traces now expose explicit routing fields
- docs and setup were aligned to the new model

## 7. Definition of Done for Architecture Alignment

The planning layer is ready when:

- docs use one architecture model
- the team understands plans vs tiers
- Phase 1 has a narrow and agreed scope
- excluded capabilities are written down clearly
- no one needs to guess where a feature belongs
