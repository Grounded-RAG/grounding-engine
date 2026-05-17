# Grounded Solution Architecture

## 1. Why This Document Exists

This document is the canonical explanation of how Grounded is designed to work.
It separates four ideas that were previously mixed together:

- user-facing subscription plans
- internal execution tiers
- namespace-level data policy
- runtime routing decisions

The main rule is simple:

- **data belongs to a tenant and namespace**
- **queries are routed to an execution tier**

Grounded is designed as a managed platform where users upload their own data and
the system provides a trustworthy RAG pipeline over that data. The system is
meant to be stronger than native/basic RAG without forcing every request through
the heaviest possible path.

---

## 2. Core Concepts

### Subscription plans

Subscription plans are commercial entitlements. They control quotas, access, and
which execution tiers a tenant is allowed to use.

Grounded uses these plan names:

- Free Plan
- Pro Plan
- Business Plan
- Enterprise Plan

### Execution tiers

Execution tiers are runtime processing modes. They control how deeply the system
processes a query.

Grounded uses these execution tiers:

- Standard Tier
- Enterprise Tier
- Critical Tier

### Namespace policy

A namespace is a tenant-scoped collection of data with its own policy.

Namespace policy is where the system records:

- domain
- sensitivity
- freshness profile
- minimum required execution tier
- whether web fallback is allowed
- whether internal model retrieval is allowed

### Effective tier

The effective tier is the final tier selected for a specific query after the
system considers:

- namespace minimum tier
- agent default tier
- router recommendation
- user-requested tier
- plan entitlement limits

---

## 3. Product Object Model

Grounded should be explained through a clear product model, not only through
backend runtime concepts.

### Organization

Top-level customer boundary for billing, members, API keys, and policy.

### Workspace

A project area inside an organization that groups datasets, agents, and chats.

### Dataset

A collection of uploaded documents plus ingestion and retrieval policy.

### Agent

A reusable assistant configured on top of one or more datasets.

### Conversation

A single chat thread inside an agent.

### Run

The execution record behind one assistant answer, including citations, mode
used, and trace metadata.

### Current backend mapping

Today the backend foundation maps to these product ideas like this:

- `Tenant` -> future organization
- `Namespace` -> future dataset
- `Document` -> uploaded file
- `IngestionJob` -> ingestion progress
- `QueryTrace` -> run / audit trail

Workspaces, agents, conversations, and runs as separate product objects are the
next product-layer additions.

---

## 4. Product Model

### Subscription plans vs execution tiers

Grounded must keep product plans and execution tiers separate.

Why:

- one tenant may pay for higher-tier access
- many of that tenant's queries should still run in Standard for speed
- only selected queries should escalate to Enterprise or Critical

If plans and execution tiers are treated as the same concept, the system becomes
hard to explain, hard to price, and hard to route safely.

### Plans-to-tier entitlements

| Subscription plan | Auto mode | Manual Standard | Manual Enterprise | Manual Critical | Notes |
|---|---|---|---|---|---|
| Free Plan | Yes | Yes | No | No | Low quotas, baseline usage |
| Pro Plan | Yes | Yes | Yes | No | Best for serious individual or small-team use |
| Business Plan | Yes | Yes | Yes | By policy | Audit and policy controls become important here |
| Enterprise Plan | Yes | Yes | Yes | Yes | Full controls, compliance, sovereign options |

### User experience model

The default user experience should be:

- `Auto (Recommended)` as the default
- optional manual override for users whose plan allows it
- clear explanation of why a tier was recommended or required

Examples:

- "Recommended: Standard because the query is simple and the namespace policy allows it."
- "Recommended: Enterprise because the query is ambiguous and freshness-sensitive."
- "Critical required because the namespace minimum tier is Critical."

### User-facing mode system

The product should expose friendly mode labels in the chat and agent UX:

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

These are not new backend tiers. They are product-facing labels that map to the
internal execution tiers:

| User-facing mode | Typical internal tier | Meaning |
|---|---|---|
| Auto | Routed dynamically | Let Grounded choose the best path |
| Instant | Standard | Fast everyday grounded answers |
| Thinking | Enterprise | Deeper retrieval for harder questions |
| Verified | Critical | Highest-assurance mode for sensitive work |

This keeps the backend architecture clear while making the UX feel more natural
to users.

---

## 5. Capability Architecture

Grounded should be described using capability groups, not a single flat list of
"stages." Some capabilities happen during ingestion, some during query-time
execution, and some are system-wide guarantees.

### Ingestion capabilities

| Capability | Description | Default placement |
|---|---|---|
| Metadata enrichment | Extract timestamps, titles, layout hints, and other quality metadata during ingestion | All tiers, because good metadata improves everything |
| Deterministic chunking baseline | Stable token-aware chunking that is easy to test and evaluate | Standard and above |
| Semantic chunking upgrade | Topic-aware chunking for better context preservation | Enterprise and above, behind evaluation/flags |

### Cross-cutting guarantees

| Capability | Description | Default placement |
|---|---|---|
| Namespace isolation | Hard multitenant data separation and policy enforcement | All tiers |
| Trace, audit, and evaluation | Record why a query used a tier, what evidence it used, and how the system behaved | All tiers |

### Retrieval and ranking capabilities

| Capability | Description | Default placement |
|---|---|---|
| Query planning and transformation | Rewrite, expansion, follow-up carryover, and execution-plan shaping | Lightweight in Standard, heavier in Enterprise and Critical |
| Hybrid retrieval with RRF | Sparse + dense retrieval merged with Reciprocal Rank Fusion | Standard and above |
| Temporal and freshness scoring | Prefer fresher evidence when the domain or namespace requires it | Enterprise and Critical |
| Reranking | Improve top-k relevance after initial retrieval | Lightweight heuristic reranking in Standard, model-based reranking in Enterprise and Critical |
| Internal model retrieval | Long-context retrieval bypass for selected corpora | Critical only |
| Corrective RAG | Retrieval quality gate and policy-controlled external fallback | Critical only |

### Generation and trust capabilities

| Capability | Description | Default placement |
|---|---|---|
| Evidence packaging and citation mapping | Select, normalize, deduplicate, and prepare evidence for the generator | Standard and above |
| Grounded generation | Generate answers only from packaged evidence | Standard and above |
| Verification loop | Critic-style verification and bounded correction loop | Critical only |
| FreshPrompt strategy | Explicit freshness/conflict handling when internal and fresh sources disagree | Critical only |
| Structured citation schema | Strict typed output with citations and validation | Standard and above |
| Degraded response and abstention | Honest fallback when evidence is weak or unsafe | Standard and above |

---

## 6. Tier Activation Matrix

| Capability | Standard Tier | Enterprise Tier | Critical Tier |
|---|---|---|---|
| Metadata enrichment | Yes | Yes | Yes |
| Deterministic / structure-aware chunking | Yes | Yes | Yes |
| Semantic chunking | No default | Feature-flagged | Allowed |
| Namespace isolation | Yes | Yes | Yes |
| Query planning and transformation | Lightweight | Heavier planner / decomposition | Yes |
| Hybrid retrieval with RRF | Yes | Yes | Yes |
| Temporal and freshness scoring | Minimal or none | Yes | Yes |
| Reranking | Lightweight heuristic | Stronger / model-based | Strongest with verification |
| Internal model retrieval | No | No default | Yes |
| Corrective RAG | No | No | Yes |
| Evidence packaging and citation mapping | Yes | Yes | Yes |
| Grounded generation | Yes | Yes | Yes |
| Verification loop | Light validation only | Lightweight only if later approved | Yes |
| FreshPrompt strategy | No | No | Yes |
| Structured citation schema | Yes | Yes | Yes |
| Degraded response and abstention | Yes | Yes | Yes |
| Trace, audit, and evaluation | Yes | Yes | Yes |

### What each tier means

**Standard Tier**

- production-safe baseline RAG
- structure-aware chunking and semi-structured document cleanup
- hybrid retrieval
- lightweight query planning and follow-up carryover
- section-aware retrieval and evidence packaging
- lightweight reranking
- structured cited output
- provider-backed generation with safe local fallback
- tracing, confidence shaping, and degraded behavior
- optimized for speed and dependable grounding

**Enterprise Tier**

- Standard plus better retrieval precision
- heavier planner for eligible queries
- temporal scoring
- model-based reranking
- stronger evidence selection

**Critical Tier**

- Enterprise plus highest-assurance verification
- corrective retrieval
- critic loop
- internal model retrieval where appropriate
- strict conflict handling and stronger fail-safe behavior

---

## 7. Basic RAG vs Grounded Standard

| Basic/native RAG | Grounded Standard Tier |
|---|---|
| Usually vector-only retrieval | Sparse + dense hybrid retrieval |
| Often raw query only | Lightweight query planning and retrieval rewrites |
| Often flat top-k chunks | Reranked and packaged evidence |
| Often little tenant isolation | Hard tenant and namespace isolation |
| Often weak citation discipline | Strict citation schema and evidence packaging |
| Often no honest degraded behavior | Explicit abstention and degraded responses |
| Often hard to audit | Traceable decisions and audit-ready metadata |
| Often prototype-oriented | Production-shaped baseline |

Grounded Standard is still a RAG system, but it is a more reliable and
trustworthy one. It is designed to be the strong baseline that all higher tiers
build on.

---

## 8. Routing Decision Flow

### Upload-time decisions

When a document is uploaded, the system assigns or resolves:

- tenant
- namespace
- domain
- sensitivity
- freshness profile
- namespace minimum tier
- whether web fallback is allowed
- whether internal model retrieval may be allowed later

These upload-time decisions create policy guardrails. They do **not** permanently
lock every future query to one tier.

### Query-time decisions

When a query arrives, the system:

1. authenticates the tenant
2. resolves the namespace and namespace policy
3. resolves the agent configuration if the query came through an agent
4. inspects query complexity and risk
5. produces a router recommendation
6. applies any user override or selected mode that the plan allows
7. computes the effective tier
8. runs the query in that tier
9. records the tier decision and reason in the trace

### Effective tier rule

```text
effective_tier = highest of:
  - namespace minimum tier
  - agent default tier
  - router recommendation
  - user requested tier

then enforce plan entitlement
```

### Safety rule

If the effective tier required for a query is higher than the tenant is allowed
to use, the system must fail clearly. It must **not** silently downgrade below
the required safety level.

---

## 9. Query and Ingestion Flows

### Ingestion flow

```text
Upload
  -> tenant and namespace resolution
  -> storage
  -> extraction
  -> metadata enrichment
  -> deterministic chunking
  -> optional semantic chunking upgrade
  -> dense index update
  -> sparse index update
  -> document ready
```

### Query flow

```text
User query
  -> authentication
  -> optional agent resolution
  -> namespace policy lookup
  -> lightweight query plan
  -> router recommendation
  -> effective tier decision
  -> sparse retrieval + dense retrieval
  -> RRF fusion
  -> optional / lightweight reranking
  -> optional temporal scoring
  -> evidence packaging
  -> grounded generation
  -> optional verification / corrective path
  -> structured cited response
  -> trace and audit record
```

---

## 10. Worked Examples

### Example 1: Simple internal policy query

- Namespace policy: `minimum_tier = standard`
- Query: "Summarize our leave policy."
- Router recommendation: Standard
- User mode: Auto
- Effective tier: Standard

Reason: simple query, low ambiguity, no high-risk policy requirement.

### Example 2: Ambiguous enterprise question

- Namespace policy: `minimum_tier = standard`
- Query: "What changed between the old and new procurement policy and what applies now?"
- Router recommendation: Enterprise
- User mode: Auto
- Effective tier: Enterprise

Reason: comparison task, ambiguity, freshness sensitivity, better retrieval
precision needed.

### Example 3: High-stakes legal query

- Namespace policy: `minimum_tier = critical`
- Agent default mode: `Verified`
- Query: "Is clause 8 still enforceable under the latest regulation?"
- Router recommendation: Critical
- User mode: Auto
- Effective tier: Critical

Reason: high-risk legal question, strong freshness and verification requirements.

---

## 11. Product Experience Summary

The ideal Grounded product flow is:

1. user joins an organization
2. user opens a workspace
3. user creates a dataset
4. user uploads documents
5. user creates an agent on top of one or more datasets
6. user starts a new chat inside that agent
7. user asks a question in `Auto`, `Instant`, `Thinking`, or `Verified`
8. system computes the effective tier safely
9. user receives an answer with citations and run details

This is the recommended direction for the full product shell around the current
backend foundation.

---

## 12. Phase 0 Alignment Results

The backend foundation has now been aligned with this architecture.

The key Phase 0 follow-ups that are now reflected in the codebase are:

- tenants use `subscription_plan` and `max_execution_tier`
- namespaces expose explicit policy fields
- query traces support routing metadata
- docs and setup now use the same plans-vs-tiers model

This means Phase 1 can start from a cleaner baseline instead of carrying forward
an ambiguous Phase 0 contract.
