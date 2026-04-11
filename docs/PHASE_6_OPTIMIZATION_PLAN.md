# Phase 6 Optimization Plan

**Status:** planned  
**Date:** 2026-04-11  
**Prerequisite:** Phases 1 through 5 are substantially complete

## Purpose

This document defines exactly what **Phase 6** means for Grounded.

Phase 6 is the **optimization and hardening** phase.

Its job is to improve:

- answer quality
- confidence calibration
- latency
- cost
- regression safety
- product trust and polish

This phase exists because a system can be architecturally complete and still
need a disciplined tuning pass before it feels consistently excellent.

---

## 1. What Is Already Live Before Phase 6

Before Phase 6 starts, the platform should already have:

- Standard baseline retrieval and grounded generation
- Enterprise retrieval intelligence
- Critical assurance features
- adaptive grounding policy support
- platform governance and operations maturity

At that point, the remaining work is not "what new capability do we invent?"

It is:

> how do we make the existing system more accurate, cheaper, faster, more
> stable, and easier to trust?

---

## 2. What Phase 6 Is Trying To Achieve

Phase 6 should answer this question:

> How do we systematically improve the quality and operational efficiency of the
> completed system without changing the product contract every week?

The expected uplift is:

- fewer quality regressions
- better confidence labels
- lower latency where possible
- lower cost for equal or better quality
- clearer trust signals for users and operators

---

## 3. What Phase 6 Includes

### 3.1 Quality optimization

Tune quality using real run failures, regression suites, and benchmark results.

Examples:

- retrieval threshold tuning
- evidence package tuning
- prompt and schema tuning
- fallback tuning
- response-shaping improvements

### 3.2 Confidence and support calibration

Improve how the system distinguishes:

- strong support
- partial support
- ambiguous support
- weak support

This should make run inspection and user trust labels more accurate.

### 3.3 Latency optimization

Profile and reduce latency across:

- retrieval
- reranking
- provider calls
- verification paths
- async orchestration

### 3.4 Cost optimization

Tune cost using:

- smarter routing
- cheaper safe defaults
- caching
- selective model usage
- prompt size controls

### 3.5 Regression automation

Expand automation around:

- benchmark suites
- replayable bad runs
- domain-specific regression fixtures
- tier-specific acceptance gates

### 3.6 UX and trust polish

Improve product trust through:

- clearer inspector labels
- better degraded wording
- clearer source disclosures
- better explanations of why a tier or policy was used

---

## 4. What Phase 6 Does Not Include

Phase 6 should **not** be used as an excuse to:

- redesign the tier model from scratch
- add unrelated major capabilities
- bypass evaluation discipline
- hide quality problems behind wording changes only

Phase 6 is for tuning and hardening, not uncontrolled scope creep.

---

## 5. Recommended Architecture Changes

### 5.1 Benchmark and replay framework

Add or strengthen tooling for:

- replaying bad runs
- comparing before/after quality
- tracking regressions by domain and tier

### 5.2 Calibration framework

Add explicit calibration checks for:

- support labels
- confidence labels
- degraded behavior

### 5.3 Profiling and observability hooks

Expand visibility into:

- per-stage latency
- model cost
- retrieval hit quality
- reranker contribution
- verifier rejection patterns

### 5.4 Optimization flags and safe rollouts

Where tuning changes are risky, ship them behind:

- config flags
- tier-specific gates
- evaluation gates

---

## 6. Suggested Build Order

The cleanest Phase 6 order is:

1. collect failure patterns from real runs
2. add benchmark coverage for those failures
3. tune support and confidence calibration
4. profile latency and cost by path
5. tune routing / thresholds / prompt sizes
6. improve trust and inspector UX
7. lock in stronger regression gates

---

## 7. Testing Strategy

Phase 6 should emphasize:

- regression replay testing
- cross-tier benchmark comparisons
- calibration testing
- latency and cost profiling
- operator and user trust checks

### Key measurements

- answer correctness
- citation correctness
- confidence calibration quality
- degraded-answer honesty
- latency per tier
- cost per run class

---

## 8. Definition Of Done

Phase 6 is complete when:

1. regressions are caught earlier and more reliably
2. confidence/support labels better reflect real evidence quality
3. latency and cost are better controlled without lowering answer quality
4. run inspection is easier for users and teammates to understand
5. the system feels stable, polished, and trustworthy in day-to-day use

---

## 9. One-Sentence Summary

Phase 6 turns the completed Grounded architecture into a more polished product
through disciplined quality tuning, calibration, latency/cost optimization, and
regression hardening.
