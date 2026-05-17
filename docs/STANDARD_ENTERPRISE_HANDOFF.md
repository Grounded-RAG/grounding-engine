# Standard And Enterprise Handoff

**Status:** current implementation handoff as of 2026-04-21

## Purpose

This document is the practical handoff guide for the current system state.

It answers:

- what is already implemented in **Standard**
- what is already implemented in **Enterprise**
- what is still left to build or harden
- what a teammate should read or inspect next before making changes

Use this as the first read if someone is continuing quality work on the system.

Related documents:

- `docs/STANDARD_TIER_CURRENT_STATE.md`
- `docs/ENTERPRISE_IMPLEMENTATION_PLAN.md`
- `docs/PHASE_2_ENTERPRISE_PLAN.md`
- `docs/NEXT_PHASES_ROADMAP.md`

---

## 1. Current Tier Snapshot

### Standard

Standard is the production baseline grounded path.

It is currently responsible for:

- everyday grounded document Q&A
- fast interactive latency
- traceable retrieval and citations
- degraded / clarification behavior when support is weak
- deterministic fallback when provider output is unavailable or rejected

### Enterprise

Enterprise is now the deeper retrieval path above Standard.

It is currently responsible for:

- harder and more ambiguous document questions
- deeper retrieval and evidence selection
- harder-query routing from `Auto`
- the backend path behind `Thinking`

### Critical

Critical is **not live yet**.

It still remains the future tier for:

- verifier / critic loops
- corrective retrieval
- highest-assurance answering
- `Verified`

---

## 2. What Is Implemented In Standard

This is the current Standard implementation in practical order.

### Ingestion and indexing

Implemented:

- document upload
- extraction for TXT / PDF / DOCX
- metadata enrichment
- structure-aware deterministic chunking
- sparse indexing in PostgreSQL
- dense indexing in Qdrant

### Retrieval

Implemented:

- hybrid sparse + dense retrieval
- Reciprocal Rank Fusion
- lightweight query planning
- lightweight query rewriting
- lightweight answerability reranking
- limited supporting-context recovery

### Evidence packaging

Implemented:

- compact evidence selection
- exact-QA-focused evidence packaging
- list / recommendation / multi-part packaging
- summary-friendly broader packaging

### Generation and answer quality

Implemented:

- Gemini-backed provider generation
- stricter Gemini schema / parser contract
- deterministic local fallback generation
- explicit answer modes
- safer unsupported refusal behavior
- deterministic arithmetic for narrow supported cases
- better exact extraction
- stricter provider validation

### Output and trust

Implemented:

- structured citations
- confidence / support shaping
- degraded responses
- clarification handling
- persisted run / query traces

### Product-shell behavior using Standard

Implemented:

- `Instant` mode backed by Standard
- `Auto` mode using Standard by default
- agent chat on top of Standard
- answer inspector / run inspector

---

## 3. What Is Implemented In Enterprise

This is the current Enterprise implementation in phase order.

### 3.1 Enterprise execution boundary

Implemented:

- Enterprise tier scaffolding
- Enterprise config flags
- Enterprise-aware routing hooks
- Enterprise-aware trace metadata

### 3.2 Reranker abstraction

Implemented:

- clean reranker interface
- disabled-safe behavior
- retrieval pipeline integration point

### 3.3 Model-backed reranking

Implemented:

- Gemini-backed Enterprise reranker
- reranker debug metadata
- safe fallback to fused ordering when reranker is unavailable

### 3.4 Hard-query routing

Implemented:

- `Thinking` routes directly to Enterprise
- `Auto` can route eligible hard queries into Enterprise
- routing reasons are explainable and traceable

### 3.5 Stronger Enterprise evidence packaging

Implemented:

- richer evidence packages for harder queries
- stronger support for multi-part and comparison-style questions
- compact packaging rules separate from Standard behavior

### 3.6 Deeper query planning

Implemented:

- stronger hard-query classification
- controlled rewrite expansion
- better planning for difficult retrieval cases

### 3.7 Temporal / freshness scoring

Implemented:

- Enterprise-only freshness-aware scoring
- recency-sensitive ranking behavior
- trace/debug support for freshness adjustments

### 3.8 Controlled query decomposition

Implemented:

- decomposition for eligible retrieval-hostile queries
- decomposition kept controlled instead of always-on

### 3.9 Evaluation coverage

Implemented:

- Enterprise benchmark coverage
- harder-query evaluation cases
- regression-oriented benchmark tests

### 3.10 Trace and debug visibility

Implemented:

- Enterprise routing reasons
- retrieval debug metadata
- evidence debug metadata
- reranker/freshness debug signals

### 3.11 Product enablement

Implemented:

- `Thinking` exposed as a live mode
- frontend wired to live capabilities
- Enterprise reranker rollout enabled by default with safe fallback

---

## 4. What Is Live In The Product Right Now

### User-facing modes

- `Auto`
- `Instant`
- `Thinking`
- `Verified` visible but disabled

### Actual backend meaning

- `Auto` -> Standard by default, can route into Enterprise for eligible hard queries
- `Instant` -> Standard
- `Thinking` -> Enterprise
- `Verified` -> not live yet

### Frontend state

Implemented:

- live capability-aware mode exposure
- chat UX with visible assistant progress
- send locked during active runs
- typing still allowed during active runs
- answer / run inspection UI

---

## 5. What Is Still Left

This section is the most important one for continuation work.

## 5.1 Standard: still worth improving

Standard is much stronger now, but it is not “finished forever.”

Still worth improving:

- broader cross-dataset evaluation
- more live-provider smoke testing
- further simplification of fallback heuristics in `llm_client.py`
- stronger claim-level groundedness checks over time
- better regression suites beyond the pilot scenarios

Important note:

- Standard should now mostly receive bug fixes, targeted accuracy fixes, and evaluation improvements
- it should not absorb Enterprise-only complexity unless clearly justified

## 5.2 Enterprise: still needs hardening

Enterprise is implemented and live, but it still needs rollout hardening.

Still left:

- broader manual smoke testing under real provider conditions
- reranker-on vs reranker-off quality comparison on live datasets
- continued benchmark expansion for harder domains
- latency / cost measurement under realistic usage
- trace inspection review to ensure debug output stays readable

## 5.3 Critical: not implemented yet

Still left for the next tier:

- verifier / critic loop
- corrective retrieval
- stricter acceptance / rejection policies
- claim-by-claim verification
- `Verified` mode activation

## 5.4 Optional Enterprise experiments

Not required for current live behavior, but possible future work:

- semantic chunking behind evaluation gates
- stronger enterprise reranker backends
- deeper recency policies

---

## 6. Clear Boundary Between Standard And Enterprise

This boundary matters and should stay clean.

### Standard should remain

- fast
- stable
- predictable
- grounded
- simpler than Enterprise

### Enterprise should remain

- deeper on hard questions
- more retrieval-intelligent
- more trace-heavy
- more expensive / higher-latency than Standard when needed

### Avoid

- copying Enterprise complexity into Standard
- using Enterprise heuristics everywhere
- making the two tiers drift into the same behavior

---

## 7. Recommended Reading Order For The Next Teammate

1. read `docs/STANDARD_ENTERPRISE_HANDOFF.md`
2. read `docs/STANDARD_TIER_CURRENT_STATE.md`
3. read `docs/ENTERPRISE_IMPLEMENTATION_PLAN.md`
4. read `docs/PHASE_2_ENTERPRISE_PLAN.md`
5. inspect these backend files:
   - `backend/app/services/query.py`
   - `backend/app/core/query_analysis.py`
   - `backend/app/services/retrieval.py`
   - `backend/app/services/evidence.py`
   - `backend/app/services/generation.py`
   - `backend/app/core/gemini_generator.py`
   - `backend/app/core/llm_client.py`
6. inspect key frontend files if working on product behavior:
   - `frontend/src/pages/AgentChatPage.tsx`
   - `frontend/src/pages/AgentsPage.tsx`
   - `frontend/src/pages/DashboardPage.tsx`
7. run targeted tests before changing anything

---

## 8. Recommended Next Work Order

If the next person is continuing from here, the best order is:

1. validate current Standard and Enterprise behavior on real datasets
2. expand evaluation coverage
3. fix any live regressions found in Standard first
4. harden Enterprise reranker and routing behavior with benchmark evidence
5. only then begin Critical / `Verified`

---

## 9. One-Sentence Summary

The system now has a strong Standard baseline and a live Enterprise path behind `Thinking`; the main remaining work is rollout hardening, broader evaluation, and the future Critical/`Verified` tier.
