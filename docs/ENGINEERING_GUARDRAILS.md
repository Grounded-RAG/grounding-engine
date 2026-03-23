# Grounded Engineering Guardrails

Purpose: keep the implementation aligned with the architecture and prevent
quality, safety, and routing rules from drifting as the system grows.

## 1. Architecture Guardrails

Before implementation starts on any feature, define:

- problem being solved
- non-goals
- success metric
- tier placement
- activation rules
- fallback behavior
- observability fields

No feature should ship without a clear answer to:

- is this a subscription-plan concern?
- is this an execution-tier concern?
- is this a namespace-policy concern?

Do not mix those concepts in one field or one ambiguous design decision.

## 2. Tier-Specific Guardrails

### Standard Tier

- planner is disabled by default
- semantic chunking is disabled by default
- reranker is disabled by default
- web fallback is disabled
- internal model retrieval is disabled
- critic loop is disabled

Standard must remain:

- fast
- stable
- grounded
- traceable

### Enterprise Tier

- planner may run only for eligible queries
- reranker and temporal scoring must be measurable
- semantic chunking must stay behind feature flags and evaluation gates
- Enterprise must not quietly inherit Critical-only behaviors

### Critical Tier

- web fallback must be allowlisted and policy-controlled
- verification retries must be bounded
- internal model retrieval must be selective, not universal
- async handoff must be available when synchronous latency is unsafe

## 3. Security and Policy Guardrails

- every request must resolve tenant context first
- every retrieval path must enforce tenant and namespace filters
- namespace policy is the safety floor
- plan entitlement is the access ceiling
- if required safety tier exceeds plan entitlement, fail clearly
- never silently downgrade below the required safety level
- do not log raw secrets or unsafe plaintext customer content

## 4. Reliability Guardrails

- define p95 latency budget before merge
- define degraded behavior before merge
- define retry and timeout policy before merge
- ingestion and indexing operations must be idempotent
- risky changes must ship behind feature flags

## 5. Evidence and Response Guardrails

- every answer must support citation mapping
- the generator must only receive packaged evidence
- the system must not return unsupported claims without degraded behavior
- if verification is incomplete, the response must say so in a controlled way
- if evidence is weak, the system must abstain or ask for clarification instead

## 6. Evaluation Guardrails

No advanced capability becomes default until it beats or matches the current
baseline on evaluation.

Every retrieval or generation change must report:

- precision@k
- recall@k
- nDCG@k
- faithfulness
- context precision
- citation validity
- degraded-response rate

Release should be blocked if:

- faithfulness drops more than 2 percent from baseline
- citation validity drops below 99.99 percent
- p95 latency regresses more than 15 percent without approval

## 7. Observability Guardrails

Every query trace must be able to answer:

- which tenant and namespace were used?
- what tier was requested?
- what tier was recommended?
- what tier was actually used?
- why was that tier chosen?
- which evidence was retrieved?
- which evidence was selected?
- did degraded behavior happen?
- did fallback or verification happen?

Every new capability must define:

- trace fields
- metrics
- failure codes
- log context

## 8. Testing Guardrails

Minimum required checks per significant feature:

- unit tests for logic and edge cases
- integration tests for service interaction
- security tests for tenant/policy boundaries
- contract tests for API schemas when applicable
- evaluation comparison when the feature changes retrieval or generation quality

Tiered behavior must be tested explicitly:

- Standard path
- Enterprise path
- Critical path
- denial or failure behavior when policy and entitlement conflict

## 9. Documentation Guardrails

Any architecture-affecting change must update the relevant docs:

- `docs/SOLUTION_ARCHITECTURE.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `README.md` when user-facing concepts change

If a change alters:

- plan entitlements
- tier behavior
- routing rules
- namespace policy

then the docs must be updated in the same batch.

## 10. PR Checklist

- [ ] Tier placement is defined
- [ ] Activation rules are defined
- [ ] Fallback behavior is defined
- [ ] Security and policy impact reviewed
- [ ] Trace and metric fields added
- [ ] Unit tests added
- [ ] Integration tests added where needed
- [ ] Evaluation impact recorded for retrieval/generation changes
- [ ] Relevant docs updated
