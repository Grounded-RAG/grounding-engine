# Next Phases Roadmap

**Status:** current planning handoff as of 2026-04-11

## Purpose

This document is the clearest "what do we build next?" guide for the team.

It is meant to answer:

- where Standard currently stands
- what Enterprise should include
- what Critical should include
- what comes after the three execution tiers
- what order the team should build things in
- how work can be split cleanly across teammates

Use this document as the operational roadmap after reading:

- `docs/STANDARD_TIER_CURRENT_STATE.md`
- `docs/SOLUTION_ARCHITECTURE.md`

---

## 1. Current Position

Grounded already has a strong Standard baseline.

The current Standard tier includes:

- structure-aware chunking
- semi-structured document cleanup
- sparse + dense hybrid retrieval
- lightweight query planning
- section-aware retrieval and evidence packaging
- lightweight reranking
- provider-backed grounded generation
- deterministic local fallback
- trace persistence
- confidence/support shaping
- degraded and clarification behavior

That means the next roadmap is no longer about "making RAG exist."

It is about building the deeper tiers in a clean order:

1. Enterprise
2. Critical
3. Adaptive Grounding
4. Platform Maturity
5. Optimization

---

## 2. Roadmap Summary

### Enterprise

Goal:

- make Grounded better on hard, ambiguous, multi-part, and freshness-sensitive
  document questions

Main product outcome:

- `Thinking` becomes a real mode

### Critical

Goal:

- make Grounded safer and more trustworthy on high-risk and high-assurance
  questions

Main product outcome:

- `Verified` becomes a real mode

### Adaptive Grounding

Goal:

- let Grounded remain evidence-first while also becoming source-aware and
  policy-aware when explanation or live augmentation is allowed

### Platform Maturity

Goal:

- make the product easier to operate, govern, deploy, and scale

### Optimization

Goal:

- tune quality, latency, cost, calibration, and user trust after the main
  architecture is in place

---

## 3. Enterprise Tier

### Enterprise purpose

Enterprise is the tier for deeper retrieval intelligence.

It should improve:

- retrieval precision
- evidence quality
- hard-query handling
- ambiguity handling
- freshness handling

It should **not** become the high-assurance verifier path. That belongs to
Critical.

### Enterprise should include

- model-based reranking
- deeper planner and query transformation
- multi-query decomposition for eligible questions
- temporal and freshness scoring
- stronger evidence packaging for harder questions
- evaluation gates for retrieval uplift
- `Thinking` mode enablement

### Enterprise should not include

- verifier / critic loop
- corrective external fallback
- internal model retrieval as a normal path
- high-assurance claim acceptance logic

### Enterprise build order

1. add Enterprise trace fields and routing metadata
2. add planner eligibility rules
3. add query rewrite / decomposition service
4. add model-based reranker interface
5. add cross-encoder reranker backend
6. wire reranker into retrieval pipeline
7. add temporal and freshness scoring
8. strengthen Enterprise evidence packaging
9. enable `Thinking`
10. run Enterprise benchmarks and fix regressions

### Enterprise workstreams that can run in parallel

#### Workstream A: planner

Focus:

- query transformation
- decomposition
- planner trace metadata

Likely files:

- `backend/app/core/query_analysis.py`
- `backend/app/services/query.py`
- `backend/app/services/generation.py`

#### Workstream B: reranking

Focus:

- reranker interface
- cross-encoder backend
- retrieval integration

Likely files:

- `backend/app/services/retrieval.py`
- `backend/app/services/evidence.py`
- `backend/app/config.py`

#### Workstream C: freshness

Focus:

- temporal scoring
- freshness-aware ordering
- dataset policy usage

Likely files:

- `backend/app/services/retrieval.py`
- `backend/app/services/trust.py`
- dataset / namespace policy models if needed

#### Workstream D: evaluation

Focus:

- Enterprise benchmark set
- planner uplift checks
- reranker uplift checks
- latency/cost measurements

Likely files:

- `backend/tests/evaluation/`
- Enterprise fixtures

#### Workstream E: docs and product wiring

Focus:

- capabilities exposure
- `Thinking` mode docs
- run inspector metadata docs

Likely files:

- `docs/`
- capabilities endpoints / schemas

### Enterprise definition of done

Enterprise is ready when:

- `Thinking` is truly backed by Enterprise retrieval behavior
- reranking is model-based and traceable
- planner usage is test-covered and inspectable
- temporal scoring is measurable and justified
- hard-query quality is better than Standard on Enterprise benchmarks
- Enterprise stays clearly separate from Critical verification behavior

---

## 4. Critical Tier

### Critical purpose

Critical is the highest-assurance grounded path.

It should improve:

- supported-claim discipline
- contradiction handling
- degradation honesty
- policy-controlled recovery

### Critical should include

- verifier / critic loop
- bounded correction behavior
- corrective retrieval orchestration
- allowlisted external fallback policy
- internal model retrieval for selected cases
- stricter unsupported-claim rejection
- richer Critical trace metadata
- async verified run path when needed
- `Verified` mode enablement

### Critical should not include

- hidden browsing
- silent source mixing
- unrestricted general-knowledge answering
- silent downgrade below a required safe tier

### Critical build order

1. add verifier contract and trace fields
2. add verifier support checks
3. add contradiction detection rules
4. add corrective retrieval orchestration
5. add allowlisted external fallback policy
6. add internal model retrieval path
7. add async verified run handling
8. enable `Verified`
9. run Critical assurance benchmarks and policy drills

### Critical workstreams that can run in parallel

#### Workstream A: verifier

Focus:

- support checking
- contradiction logic
- bounded answer rejection

#### Workstream B: corrective retrieval

Focus:

- retry orchestration
- fallback policy enforcement
- retrieval correction logic

#### Workstream C: async execution

Focus:

- long-running verified jobs
- status inspection
- resumable run visibility

#### Workstream D: policy and governance hooks

Focus:

- dataset policy enforcement
- external fallback controls
- run metadata and audit clarity

#### Workstream E: evaluation and drills

Focus:

- unsupported-claim reduction
- false rejection rate
- policy test coverage
- high-risk regression scenarios

### Critical definition of done

Critical is ready when:

- `Verified` is real and traceable
- Critical measurably reduces unsupported answers in high-risk scenarios
- fallback stays allowlisted and policy-controlled
- the system clearly degrades rather than overclaims
- Critical remains stricter than both Standard and Enterprise

---

## 5. Adaptive Grounding

### Adaptive Grounding purpose

This phase makes Grounded source-aware without abandoning its trust contract.

It should let the system remain:

- strictly grounded when required
- explanation-capable when policy allows
- live-augmented when policy allows

### Adaptive Grounding should include

- grounding policies:
  - `Strict`
  - `Balanced`
  - `Live`
- pluggable generator abstraction
- source-aware routing
- explicit model-knowledge augmentation with disclosure
- optional live augmentation with disclosure
- richer answer composition by source type

### Adaptive Grounding build order

1. add grounding policy model
2. add generator abstraction
3. add prompt assembly layer
4. add source-aware router
5. add balanced-mode disclosure path
6. add live-mode disclosure path
7. add source-usage run metadata
8. expand source-aware evaluation

### Adaptive Grounding definition of done

This phase is ready when:

- the system can clearly distinguish grounded vs model-derived vs live content
- source usage is disclosed instead of hidden
- policy-denied source expansion is blocked reliably
- mixed-source responses remain auditable

---

## 6. Platform Maturity

### Platform Maturity purpose

This phase makes the product easier to run in real organizations.

### Platform Maturity should include

- connectors and recurring sync
- governance and identity controls
- usage metering
- billing visibility
- admin and operator tooling
- observability and alerts
- deployment hardening

### Platform Maturity build order

1. metering model
2. governance and audit model
3. admin APIs and settings
4. connector framework and first sources
5. sync monitoring and operations dashboards
6. deployment and security hardening

### Platform Maturity definition of done

This phase is ready when:

- organizations can govern usage cleanly
- connectors are inspectable and reliable
- operators can support the product at scale
- usage/billing records are trustworthy

---

## 7. Optimization Phase

### Optimization purpose

Optimization is the final hardening phase after the major tier architecture is
in place.

This phase is where the team tunes:

- answer quality
- latency
- cost
- confidence calibration
- user trust signals
- evaluation coverage

Optimization is not a replacement for earlier phases.
It is the structured pass that turns a working product into a polished one.

### Optimization should include

- quality tuning from real run data
- confidence and support calibration
- latency and cost profiling
- benchmark expansion across domains
- regression automation
- UX trust and inspector polish

### Optimization build order

1. collect real usage failure patterns
2. expand benchmarks around those failures
3. tune retrieval and generation thresholds
4. tune confidence and support calibration
5. reduce latency and cost regressions
6. improve inspector/debug visibility
7. re-run quality and trust gates

### Optimization definition of done

Optimization is ready when:

- quality regressions are caught earlier
- confidence labels better match real support
- latency/cost remain reasonable for each mode
- the product feels stable and understandable to users

---

## 8. Recommended Overall Build Order

This is the cleanest overall sequence for the team:

1. freeze Standard except for bug fixes and maintenance
2. build Enterprise
3. enable `Thinking`
4. build Critical
5. enable `Verified`
6. build Adaptive Grounding
7. build Platform Maturity
8. run Optimization as the final hardening phase

---

## 9. Recommended Team Structure

To work in parallel without stepping on each other:

- one issue should have one clear owner
- each owner should ship:
  - code
  - tests
  - docs
  - PR notes

Recommended split for upcoming work:

- retrieval / reranking owner
- planner / routing owner
- verification owner
- platform / governance owner
- evaluation / docs owner

This keeps the write scopes clearer and makes reviews easier.

---

## 10. What To Read Next

If a teammate is starting work after Standard, the reading order should be:

1. `docs/STANDARD_TIER_CURRENT_STATE.md`
2. `docs/SOLUTION_ARCHITECTURE.md`
3. this document
4. the specific phase doc they are implementing:
   - `docs/PHASE_2_ENTERPRISE_PLAN.md`
   - `docs/PHASE_3_CRITICAL_PLAN.md`
   - `docs/PHASE_4_ADAPTIVE_GROUNDING_PLAN.md`
   - `docs/PHASE_5_PLATFORM_MATURITY_PLAN.md`
   - `docs/PHASE_6_OPTIMIZATION_PLAN.md`

---

## 11. One-Sentence Summary

Grounded now has a strong Standard baseline; the next roadmap is to build
Enterprise for deeper retrieval, Critical for higher assurance, Adaptive
Grounding for source-aware intelligence, Platform Maturity for operations, and
Optimization for final quality and trust tuning.
