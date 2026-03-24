# Phase 4 Adaptive Grounding Plan

**Status:** planned  
**Date:** 2026-03-24  
**Prerequisite:** Phase 3 Critical tier is complete

## Purpose

This document defines exactly what **Phase 4** means for Grounded.

Phase 4 is the **adaptive grounding and source-aware intelligence** phase.

Its job is to evolve Grounded from a strictly dataset-first RAG platform into a
source-aware reasoning system that can:

- stay strictly grounded when required
- use model knowledge when policy allows
- use live or external context when policy allows
- disclose exactly which source types shaped the answer

Phase 4 does **not** replace the tier model.
Instead, it adds a new layer that sits alongside the existing tiers:

- grounding policy

This phase is where Grounded stops being only "retrieve then answer" and
becomes a source-aware assistant without weakening the trust contract.

---

## 1. What Is Already Live Before Phase 4

Before Phase 4 starts, the platform already has:

- Phase 1 Standard baseline
- Phase 1.5 product shell
- Phase 2 Enterprise retrieval upgrades
- Phase 3 Critical verification and corrective retrieval

That means the system already knows how to:

- ingest and retrieve enterprise data
- choose deeper retrieval paths
- verify high-risk answers
- expose citations and run details

Phase 4 builds on top of that strong trust foundation.

---

## 2. What Phase 4 Is Trying To Achieve

Phase 4 should answer this question:

> How do we let Grounded explain, compare, clarify, and assist beyond strict
> document quoting without turning it into an opaque general chatbot?

The expected uplift is:

- better handling of ambiguous follow-up questions
- better explanations of terms, concepts, and implications
- better user retention inside Grounded for general follow-up work
- explicit disclosure of grounded versus model-derived versus live information
- stronger handling of questions that sit between "document lookup" and
  "general reasoning"

In product terms, this phase introduces a new policy dimension:

- `Strict`
- `Balanced`
- `Live`

These are **grounding policies**, not new execution tiers.

---

## 3. What Phase 4 Includes

Phase 4 includes these capabilities:

### 3.1 Grounding policy model

Grounded should add a clear grounding policy model with discrete options:

- `Strict`
- `Balanced`
- `Live`

Recommended meanings:

- `Strict`: answer only from dataset evidence; degrade or abstain when support
  is weak
- `Balanced`: prioritize dataset evidence but allow model knowledge for
  explanation, synthesis, or gap-filling with explicit disclosure
- `Live`: dataset evidence first, then policy-controlled model knowledge and
  live or external context when allowed

Important rule:

- do not use a vague continuous `0.0 to 1.0` slider as the main control
- discrete grounding policies are easier to explain, audit, and enforce

### 3.2 Pluggable LLM-backed generation layer

Grounded should add a generator abstraction that supports:

- deterministic local generator
- local model generator
- hosted provider generator

Possible providers later may include:

- Gemini
- OpenAI
- Anthropic
- Ollama or local providers

This phase should make the generator pluggable without making the system depend
on one vendor.

### 3.3 Source-aware router

Grounded should add a router that classifies the source requirements of the
query, for example:

- `internal_only`
- `internal_plus_explanation`
- `general_only`
- `live_required`

The router should consider:

- grounding policy
- dataset policy
- user question type
- retrieval quality
- safety constraints

### 3.4 Explicit model-knowledge augmentation

When policy allows it, the system should be able to use model knowledge for:

- concept explanation
- industry-standard comparisons
- clarifying terminology
- drafting or reframing around grounded content

Important rules:

- model knowledge must be explicitly disclosed
- unsupported grounded claims must not be replaced with hidden model guesses
- grounded and ungrounded content must remain distinguishable

### 3.5 Live or external augmentation with disclosure

When both grounding policy and dataset policy allow it, Grounded should support
live or external augmentation with explicit disclosure.

Expected behavior:

- dataset evidence remains first priority
- external context must be clearly labeled
- contradictory source types should not be flattened into one hidden narrative

### 3.6 Source-aware answer composition

Answers should become more structured and source-aware.

Recommended answer structure:

- grounded answer section
- cited evidence section
- model-knowledge explanation section when used
- live or external context section when used
- source disclosure summary

### 3.7 Richer run metadata and answer disclosures

Runs should record:

- source types used
- grounding policy used
- whether model knowledge was used
- whether live context was used
- whether the answer mixed sources
- disclosure text or flags

---

## 4. What Phase 4 Does Not Include

Phase 4 should **not** include:

- hidden mixing of grounded and ungrounded content
- removal of citations when evidence exists
- vague or misleading "AI knows best" behavior
- unrestricted creative mode inside the same trust contract as grounded work
- bypassing dataset policy or plan entitlements

Grounded should expand its intelligence without abandoning its evidence-first
identity.

---

## 5. Product Meaning Of Adaptive Grounding

Phase 4 does not add a new tier.
It adds a new product and policy layer.

### Grounding policies

| Grounding policy | Meaning | Best for |
|---|---|---|
| Strict | Only dataset evidence | Legal, compliance, audit, policy |
| Balanced | Dataset-first plus explained model knowledge | Research, strategy, onboarding, technical support |
| Live | Dataset-first plus live or external augmentation | Freshness-sensitive, changing domains, monitoring |

### Important separation

Keep these separate:

- subscription plan
- user-facing mode
- execution tier
- grounding policy

That separation keeps the product understandable.

---

## 6. Runtime Model In Phase 4

### User-facing modes

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

### Internal execution tiers

- `Standard`
- `Enterprise`
- `Critical`

### Grounding policies

- `Strict`
- `Balanced`
- `Live`

### Runtime behavior

At query time, the system should decide:

1. which execution tier is required
2. which grounding policy is allowed
3. which source types may be used
4. how the final answer must disclose those sources

### Important rule

The system must never silently use a broader source policy than the dataset,
agent, tenant, or user is allowed to use.

---

## 7. Recommended Architecture Changes

### 7.1 Generator abstraction

Add a generator interface capable of supporting:

- deterministic generation
- local LLM-backed generation
- hosted LLM-backed generation

Recommended outputs:

- answer text
- cited spans
- disclosure sections
- formatting structure

### 7.2 Prompt assembly layer

Add a prompt assembly layer that can combine:

- user query
- selected evidence
- agent instructions
- grounding policy
- allowed source types
- output schema requirements

### 7.3 Source-policy router

Add a routing service responsible for:

- query classification by source need
- source-usage policy enforcement
- escalation from internal-only to balanced or live paths only when allowed

### 7.4 Answer disclosure model

Add an answer-disclosure model responsible for:

- identifying grounded versus model-derived versus live-derived segments
- producing user-visible disclosure summaries
- enforcing response-shaping rules that keep source classes explicit

### 7.5 Trace and run expansion

Add richer run metadata such as:

- `grounding_policy_used`
- `source_types_used`
- `model_knowledge_used`
- `live_context_used`
- `disclosure_generated`
- `source_mix_reason`

---

## 8. Data And API Impact

Phase 4 should prefer evolving the current APIs.

### Endpoints that should stay stable

- `POST /v1/query`
- `POST /v1/agents/{agent_id}/chat`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/capabilities`

### Suggested schema additions

Potential additions to responses:

- `grounding_policy`
- `source_types_used`
- `knowledge_disclosure`
- `grounded_sections`
- `general_knowledge_sections`
- `live_context_sections`

### Suggested agent and dataset additions

Potential future fields:

- `Agent.grounding_policy`
- `Dataset.allowed_fallback_behavior`
- `Dataset.allow_live_augmentation`

---

## 9. Suggested Build Order

The cleanest Phase 4 order is:

1. grounding policy model
2. generator abstraction
3. prompt assembly layer
4. source-aware router
5. balanced generation path with disclosure
6. live augmentation path with disclosure
7. response schema and run metadata expansion
8. evaluation and policy tuning

This keeps the trust rules in place while adding intelligence gradually.

---

## 10. Testing Strategy

Phase 4 needs both quality and trust testing.

### Unit tests

Add unit tests for:

- grounding policy enforcement
- source-router decisions
- disclosure generation rules
- generator selection logic

### Integration tests

Add integration tests for:

- strict grounded path
- balanced path with disclosure
- live path with disclosure
- policy-denied source expansion
- run metadata for mixed-source answers

### Evaluation tests

Measure:

- groundedness
- hallucination rate
- ambiguity resolution quality
- disclosure accuracy
- user-perceived answer completeness
- latency and cost impact

### Manual / Swagger validation

Phase 4 Swagger checks should extend the flow with:

- agent or dataset grounding-policy inspection
- runs showing source types used
- answers that explicitly disclose grounded vs model knowledge content

---

## 11. Definition Of Done

Phase 4 is complete when:

1. Grounded supports explicit grounding policies
2. the generator layer is provider-agnostic and pluggable
3. mixed-source answers remain clearly disclosed and traceable
4. the system never hides when it goes beyond the dataset
5. hallucination and ambiguity handling measurably improve on allowed paths
6. the trust contract remains intact

---

## 12. Clear Boundary With Phase 5

Phase 4 should stop at:

- source-aware reasoning
- generator abstraction
- controlled model and live augmentation
- explicit disclosures

Phase 5 begins when the system focuses on:

- connectors and sync
- enterprise governance
- large-scale operations
- deployment and admin maturity

---

## 13. One-Sentence Summary

Phase 4 makes Grounded source-aware by adding grounding policies, pluggable
LLM-backed generation, and explicit disclosure when answers use more than
retrieved dataset evidence.
