# Documentation Alignment Plan

**Status:** implemented on 2026-03-21  
**Purpose:** keep one short planning note that points the team to the canonical
architecture docs.

## What This Plan Did

The documentation redesign locked in these architecture decisions before any
Phase 1 implementation work:

- subscription plans are separate from execution tiers
- user-facing modes are separate from internal tiers
- plans are:
  - Free
  - Pro
  - Business
  - Enterprise
- product-facing modes are:
  - Auto
  - Instant
  - Thinking
  - Verified
- execution tiers are:
  - Standard
  - Enterprise
  - Critical
- data belongs to tenant + namespace
- queries are routed to an effective tier
- `Auto (Recommended)` is the default UX
- manual tier override is allowed only within plan entitlements

## Canonical Documents

Use these files as the source of truth:

- `docs/PRODUCT_FLOW.md`
- `docs/SOLUTION_ARCHITECTURE.md`
- `docs/STANDARD_TIER_CURRENT_STATE.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/PHASE_1_5_BACKEND_PLAN.md`
- `docs/PHASE_2_ENTERPRISE_PLAN.md`
- `docs/PHASE_3_CRITICAL_PLAN.md`
- `docs/PHASE_4_ADAPTIVE_GROUNDING_PLAN.md`
- `docs/PHASE_5_PLATFORM_MATURITY_PLAN.md`
- `docs/ENGINEERING_GUARDRAILS.md`
- `docs/BRIEF.md`

## What Was Fixed In Phase 0.5

The architecture-alignment follow-ups are now complete:

- `Tenant.plan_tier` was replaced with:
  - `subscription_plan`
  - `max_execution_tier`
- namespace policy fields were added explicitly
- query traces were made routing-aware
- README and architecture docs now use the same vocabulary

## Phase Order

- Phase 0: backend foundation and safety
- Phase 0.5: architecture alignment and Phase 0 audit
- Phase 1: Standard tier
- Phase 1.5: product shell and workspace model
- Phase 2: Enterprise tier
- Phase 3: Critical tier
- Phase 4: adaptive grounding and source-aware intelligence
- Phase 5: platform maturity

## Backend Next Step

The next concrete backend phase is `Phase 2`.

Current delivered state:

1. Phase 1 Standard backend is complete
2. the current Standard implementation handoff is documented in:
   - `docs/STANDARD_TIER_CURRENT_STATE.md`
3. Phase 1.5 product-shell backend is complete
4. the frontend shell is now integrated against the current backend contracts

Phase 2 build order:

1. planner / query transformation for eligible queries
2. temporal and freshness scoring
3. reranking
4. semantic chunking experiment behind flags and evaluation
5. `thinking` mode activation on top of the Enterprise path
6. Enterprise benchmarks and evaluation gates

Detailed Phase 2 plan:

- `docs/PHASE_2_ENTERPRISE_PLAN.md`

Longer-term roadmap after Phase 2:

- Phase 3 Critical assurance:
  - `docs/PHASE_3_CRITICAL_PLAN.md`
- Phase 4 adaptive grounding and source-aware intelligence:
  - `docs/PHASE_4_ADAPTIVE_GROUNDING_PLAN.md`
- Phase 5 platform maturity:
  - `docs/PHASE_5_PLATFORM_MATURITY_PLAN.md`

## Team Rule

If any future change affects plans, tiers, namespace policy, or routing, update
the canonical docs in the same batch as the code change.
