# Phase 3 Critical Plan

**Status:** planned  
**Date:** 2026-03-24  
**Prerequisite:** Phase 1 Standard, Phase 1.5 product shell, and Phase 2
Enterprise retrieval upgrades are complete

## Purpose

This document defines exactly what **Phase 3** means for Grounded.

Phase 3 is the **Critical tier**.

Its job is to add the highest-assurance runtime path for difficult, risky, and
high-stakes questions where retrieval precision alone is not enough.

Phase 3 is where Grounded turns on the real backend path behind:

- `Verified`

It is the phase where the platform moves from "better retrieval" to
"stronger verification, corrective behavior, and policy-controlled recovery."

---

## 1. What Is Already Live Before Phase 3

Before Phase 3 starts, the platform already has:

- Phase 1 Standard ingestion and query
- hybrid retrieval with dense + sparse search and RRF
- evidence packaging and structured citations
- degraded response behavior
- trace persistence
- Phase 1.5 product-shell backend:
  - workspaces
  - datasets
  - agents
  - conversations
  - messages
  - runs
  - dashboard
  - API key management
- Phase 2 Enterprise retrieval upgrades:
  - planner for eligible queries
  - temporal and freshness scoring
  - reranking
  - stronger evidence selection
  - `Thinking` enabled

Current expected mode behavior at the end of Phase 2:

- `Auto` -> Standard or Enterprise
- `Instant` -> Standard
- `Thinking` -> Enterprise
- `Verified` -> visible but disabled

So Phase 3 starts from a strong product and a strong retrieval stack.

---

## 2. What Phase 3 Is Trying To Achieve

Phase 3 should answer this question:

> How do we make Grounded safer and more trustworthy when the query is
> high-risk, freshness-sensitive, or likely to produce unsupported claims
> without silently guessing?

The expected Critical uplift is:

- fewer unsupported claims in high-risk scenarios
- better behavior when retrieval is weak or contradictory
- explicit verification before a final answer is accepted
- policy-controlled recovery paths when internal evidence is insufficient
- stronger traceability for why an answer was accepted, rejected, or degraded

In product terms:

- `Verified` becomes real
- `Auto` can route into Critical when policy or risk requires it
- users get a visibly safer path for legal, compliance, policy, medical, or
  other high-stakes tasks

---

## 3. What Phase 3 Includes

Phase 3 includes these capabilities:

### 3.1 Verification / critic loop

Critical adds an explicit verification stage after answer construction.

The verifier should be responsible for:

- checking whether the answer is sufficiently supported by retrieved evidence
- rejecting unsupported or weakly supported claims
- identifying contradictions between evidence and answer
- deciding whether bounded correction should be attempted

Important rule:

- the verifier is not a free-form second generator
- it is a bounded assurance component with clear acceptance and rejection rules

### 3.2 Corrective RAG with allowlisted web fallback

Critical adds corrective behavior when internal retrieval is weak.

Corrective behavior may include:

- retrying retrieval with planner assistance
- switching retrieval emphasis
- using an allowlisted external source policy when dataset and tenant policy
  permit it

Important rules:

- no uncontrolled web search
- no silent browsing
- no external fallback unless explicitly allowed by policy

### 3.3 Internal Model Retrieval

Critical adds an internal long-context retrieval path for selected corpora.

This is useful when:

- the corpus is small enough to fit into a stronger long-context path
- the use case benefits from full-document reasoning
- the system needs an internal recovery path before external fallback

Important rule:

- this is a selective tool, not the default path for all queries

### 3.4 FreshPrompt conflict-resolution behavior

Critical should introduce explicit conflict handling when:

- internal documents disagree with fresher evidence
- policy documents conflict with recent updates
- multiple evidence sources disagree in ways that matter for safety

FreshPrompt behavior should:

- make source conflicts explicit
- avoid collapsing contradictory evidence into one misleading answer
- prefer the right source according to policy and freshness logic

### 3.5 Strict unsupported-claim handling

Critical should be stricter than Standard or Enterprise when support is weak.

Expected behavior:

- abstain rather than overclaim
- degrade rather than speculate
- distinguish:
  - fully supported claims
  - partially supported claims
  - unsupported claims

### 3.6 Async verified query path

Some Critical requests will be too expensive or slow for a tight synchronous
timeout.

Critical should therefore support an async verified path for:

- long-running reviews
- large evidence sets
- retry-heavy verification workflows
- policy-driven high-assurance requests

This path should remain inspectable and auditable.

### 3.7 Critical policy tests and drills

Critical needs stronger operational confidence than earlier phases.

This phase should therefore include:

- policy tests
- failure drills
- fallback drills
- verifier rejection tests
- high-risk scenario regression sets

---

## 4. What Phase 3 Does Not Include

Phase 3 should **not** include:

- uncontrolled public web search
- hidden source mixing
- generic "creative AI" behavior
- unrestricted general-knowledge answering
- silent downgrade below the required safe tier

Those behaviors would weaken the trust model instead of improving it.

---

## 5. Product Meaning Of Critical

Critical is the backend path behind:

- `Verified`

### Product promise

`Verified` should mean:

- highest-assurance path
- stricter trust controls
- stronger unsupported-claim handling
- bounded correction and recovery behavior
- more latency in exchange for higher confidence

### Product promise it should not make

It should **not** promise:

- perfect truth
- unrestricted live research
- instant answers for every request
- invisible recovery behavior

Critical should feel safer, not magical.

---

## 6. Runtime Model In Phase 3

### User-facing modes

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

### Internal execution tiers

- `Standard`
- `Enterprise`
- `Critical`

### Phase 3 runtime behavior

| User-facing mode | Phase 3 backend behavior |
|---|---|
| `auto` | route to Standard, Enterprise, or Critical depending on eligibility |
| `instant` | route to Standard |
| `thinking` | route to Enterprise |
| `verified` | route to Critical |

### Important routing rule

The system should still respect:

- dataset minimum tier
- tenant entitlement
- plan limits
- sensitivity rules
- freshness rules
- external fallback policy

The system must never silently run below the required safe tier floor.

---

## 7. Recommended Architecture Changes

### 7.1 Verifier service

Add a dedicated verification service responsible for:

- answer support checks
- contradiction checks
- verifier outcome recording
- bounded correction decisions

Recommended outputs:

- verifier applied
- verifier decision
- rejection reason
- correction attempted
- correction outcome

### 7.2 Corrective retrieval orchestration

Add a corrective retrieval orchestrator responsible for:

- retrying retrieval when support is weak
- invoking alternative retrieval strategies
- invoking allowlisted external fallback only when policy allows

Recommended outputs:

- corrective path applied
- corrective reason
- external fallback used
- external source class used

### 7.3 Internal model retrieval path

Add an internal long-context retrieval path for selected datasets or corpus
classes.

The system should record:

- whether internal model retrieval was used
- why it was used
- whether it improved or replaced the primary evidence package

### 7.4 Richer trace and run metadata

Critical should record richer trace details such as:

- verifier applied
- verifier decision
- corrective retrieval applied
- external fallback applied
- fallback source class
- internal model retrieval applied
- FreshPrompt conflict status
- final acceptance / degradation reason

### 7.5 Async orchestration support

Critical should add durable orchestration support for:

- long-running verified requests
- retries
- final status inspection
- resumable or inspectable run state

---

## 8. Data And API Impact

Phase 3 should prefer evolving the current APIs rather than replacing them.

### Endpoints that should stay stable

- `POST /v1/query`
- `POST /v1/agents/{agent_id}/chat`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/capabilities`

### What changes in behavior

- `Verified` becomes enabled in capabilities
- `Auto` may route some queries to Critical
- runs expose verifier and corrective metadata
- long-running verified paths may require async run inspection

### Suggested trace / run additions

Potential fields to add:

- `verification_applied`
- `verification_outcome`
- `verification_reason`
- `corrective_rag_applied`
- `external_fallback_applied`
- `external_fallback_reason`
- `internal_model_retrieval_applied`
- `source_conflict_detected`
- `critical_activation_reason`

---

## 9. Suggested Build Order

The cleanest Phase 3 order is:

1. verifier contract and trace fields
2. verifier decision logic
3. corrective retrieval orchestration
4. allowlisted external fallback policy
5. internal model retrieval path
6. FreshPrompt conflict handling
7. async verified run path
8. capabilities update to enable `verified`
9. evaluation and policy drill pass

This keeps the safety-critical changes bounded and testable.

---

## 10. Testing Strategy

Phase 3 needs stronger testing than earlier phases because the system is now
responsible for deciding whether an answer is safe enough to return.

### Unit tests

Add unit tests for:

- verifier decision logic
- contradiction detection rules
- corrective-retrieval eligibility
- external fallback policy logic
- FreshPrompt conflict handling

### Integration tests

Add integration tests for:

- `Verified` mode request path
- `Auto` routing into Critical
- verifier rejection behavior
- corrective retrieval activation
- external fallback denial when policy blocks it
- async verified run lifecycle

### Evaluation tests

Measure:

- unsupported-claim reduction
- verifier rejection rate
- false-rejection rate
- external-fallback activation rate
- high-risk scenario coverage
- latency impact

### Manual / Swagger validation

Phase 3 Swagger checks should extend the current flow with:

- `GET /v1/capabilities` showing `verified` enabled
- `POST /v1/agents/{agent_id}/chat` with `mode = "verified"`
- run inspection showing verifier and corrective metadata
- async verified run inspection if applicable

---

## 11. Definition Of Done

Phase 3 is complete when:

1. `Verified` is truly enabled and backed by the Critical path
2. Critical measurably reduces unsupported claims in high-risk scenarios
3. verifier and corrective behavior are traceable and test-covered
4. external fallback remains allowlisted and policy-controlled
5. the system never silently downgrades below the required safety floor
6. Critical remains distinct from both Standard and Enterprise

---

## 12. Clear Boundary With Phase 4

Phase 3 should stop at:

- highest-assurance verification
- corrective retrieval
- bounded external fallback
- strong conflict handling

Phase 4 begins when Grounded expands into:

- adaptive grounding policies
- explicit model-knowledge augmentation
- source-aware answer composition
- pluggable LLM-backed generation across grounded policies

That boundary should stay clean.

---

## 13. One-Sentence Summary

Phase 3 makes Grounded safer on high-risk questions by turning `Verified` into
a real Critical path with verification, corrective retrieval, and strongly
traceable assurance behavior.
