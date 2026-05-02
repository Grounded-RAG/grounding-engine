# Grounded System Design

## 1. Executive Summary

Grounded is a reliability-first RAG platform for user-owned documents. Users
upload data into tenant-scoped namespaces, then query that data through a routed
execution model that balances speed, accuracy, and verification depth.

This design intentionally separates:

- subscription plans
- user-facing modes
- execution tiers
- namespace policy
- runtime routing

That separation is essential for a trustworthy platform. The same customer can
own many datasets, and the same dataset can support simple and high-risk queries
that need different execution depth.

---

## 2. Terminology

### `subscription_plan`

Billing and entitlement concept. Controls quotas, allowed execution tiers, and
advanced platform access.

### `execution_tier`

Runtime query-processing mode. Grounded uses:

- Standard Tier
- Enterprise Tier
- Critical Tier

### `namespace_policy`

Namespace-level rules that affect routing and safety. At minimum this policy
should cover:

- domain
- sensitivity
- freshness profile
- minimum required tier
- whether web fallback is allowed
- whether internal model retrieval is allowed

### `effective_tier`

The final tier selected for a query after the system considers:

- namespace minimum tier
- agent default tier
- router recommendation
- user requested tier
- plan entitlement limit

### `mode`

The product-facing label used in the UI to express depth and assurance. Grounded
should expose:

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

These labels map to the internal execution tiers but are not the same thing as
the tiers themselves.

### `grounding_policy`

Source-usage policy that controls whether the answer may use:

- only dataset evidence
- dataset evidence plus model knowledge
- dataset evidence plus policy-controlled live context

Recommended future policies:

- `Strict`
- `Balanced`
- `Live`

### Important rule

- data belongs to tenant + namespace
- queries are routed to an effective tier

Data does **not** permanently belong to one execution tier.

---

## 3. Product Model

### 3.1 Subscription plans

Grounded uses these user-facing plans:

- Free Plan
- Pro Plan
- Business Plan
- Enterprise Plan

These are commercial entitlements, not runtime modes.

| Subscription plan | Auto mode | Manual Standard | Manual Enterprise | Manual Critical | Notes |
|---|---|---|---|---|---|
| Free Plan | Yes | Yes | No | No | Lowest quotas, baseline path only |
| Pro Plan | Yes | Yes | Yes | No | Good for advanced individual and small-team use |
| Business Plan | Yes | Yes | Yes | By policy | Better controls and broader operational access |
| Enterprise Plan | Yes | Yes | Yes | Yes | Full controls, compliance, sovereign options |

### 3.2 Why plans are not tiers

Plans answer:

- what the tenant is allowed to use
- how much they can use

Execution tiers answer:

- how deeply a specific query should be processed

The same Pro tenant may run one query in Standard and another in Enterprise.
The same Enterprise tenant may run many low-risk queries in Standard for speed.

### 3.3 Why modes are not tiers

Modes are the UX layer. Tiers are the runtime layer.

Recommended mapping:

| Mode | Typical tier | Product meaning |
|---|---|---|
| Auto | Routed dynamically | Let Grounded choose |
| Instant | Standard | Fast everyday grounded answers |
| Thinking | Enterprise | Deeper retrieval for harder queries |
| Verified | Critical | Highest-assurance mode |

This lets the UI feel intuitive without weakening the backend safety model.

---

## 4. Product Object Model

The product should be built around these top-level objects:

- Organization
- Workspace
- Dataset
- Agent
- Conversation
- Run
- API Key

### Recommended meanings

- Organization: billing, members, API keys, policy
- Workspace: project area inside the organization
- Dataset: uploaded documents plus ingestion/retrieval policy
- Agent: reusable assistant attached to one or more datasets and a grounding policy
- Conversation: one chat thread inside an agent
- Run: one execution record behind one answer

### Current backend mapping

Today the backend foundation maps to the future product shell like this:

- `Tenant` -> organization
- `Workspace` -> workspace
- `Namespace` -> dataset storage model
- `Dataset` API -> product-facing dataset
- `Agent` -> agent
- `Conversation` -> conversation
- `Message` -> message history
- `Document` -> uploaded file
- `IngestionJob` -> ingestion progress
- `QueryTrace` + Run API -> run / audit record

The backend therefore already includes the first product-shell layer and the
next phases focus on deeper intelligence, assurance, and platform maturity.

---

## 5. Capability Architecture

Not every capability is a single linear runtime stage. Grounded is better
understood as a grouped capability architecture.

### 4.1 Ingestion capabilities

- Metadata enrichment
- Deterministic chunking baseline
- Semantic chunking upgrade

### 4.2 Cross-cutting guarantees

- Namespace isolation and access-controlled retrieval
- Trace, audit, and evaluation layer

### 4.3 Retrieval and ranking capabilities

- Query planning and transformation
- Hybrid retrieval with RRF
- Temporal and freshness scoring
- Reranking
- Internal model retrieval
- Corrective RAG

### 4.4 Generation and trust capabilities

- Evidence packaging and citation mapping
- Grounded generation
- Verification loop
- FreshPrompt strategy
- Grounding policy and source-aware generation
- Structured citation schema
- Degraded response and abstention behavior

---

## 6. Technology Defaults

These defaults remain the reference design until explicitly changed:

- sparse retrieval for v1: PostgreSQL FTS
- dense retrieval for v1: Qdrant
- chunking baseline: deterministic token-aware chunking
- semantic chunking: evaluated upgrade, not default
- planner: Enterprise and Critical by default
- web fallback: Critical only
- internal model retrieval: Critical only
- trace retention default: redacted traces

---

## 7. Runtime Execution Model

### 6.1 Upload and ingestion flow

```text
Upload
  -> authenticate tenant
  -> resolve namespace and namespace policy
  -> store canonical file
  -> extract text
  -> enrich metadata
  -> deterministic chunking
  -> optional semantic chunking upgrade
  -> write dense and sparse indexes
  -> mark document ready
```

### Upload-time decisions

At upload time the system should assign:

- tenant
- namespace
- domain
- sensitivity
- freshness profile
- namespace minimum tier
- whether web fallback is allowed
- whether internal model retrieval may be allowed later

These decisions define guardrails. They do not permanently force every future
query into one tier.

### 6.2 Query execution flow

```text
User query
  -> authentication
  -> optional agent resolution
  -> namespace policy lookup
  -> router recommendation
  -> effective tier decision
  -> sparse retrieval + dense retrieval
  -> RRF fusion
  -> optional reranking
  -> optional temporal scoring
  -> evidence packaging
  -> grounded generation
  -> optional verification or corrective path
  -> structured cited response
  -> trace and audit record
```

### Query-time decisions

At query time the system should:

1. authenticate tenant access
2. resolve namespace policy
3. resolve the agent if the query came through an agent
4. inspect query complexity, ambiguity, and risk
5. produce a router recommendation
6. accept a user override or mode selection if the plan allows it
7. compute the effective tier
8. execute the tier path
9. record `tier_used` and `routing_reason` in the trace

### Routing rule

```text
effective_tier = highest of:
  - namespace minimum tier
  - agent default tier
  - router recommendation
  - user requested tier

then enforce plan entitlement
```

### Safety rule

If the tier required to answer safely is higher than the tenant is allowed to
use, the request must fail clearly. The system must not silently downgrade below
the required safety level.

### Trace capture

Every query trace should capture at least:

- tenant_id
- namespace_id
- requested_tier
- router_recommendation
- effective_tier
- routing_reason
- retrieved evidence ids
- selected evidence ids
- degraded reasons
- verifier outcome

---

## 8. Tier Activation Model

### 7.1 Standard Tier

Standard is the production-grade baseline.

Enabled:

- namespace isolation
- metadata enrichment
- deterministic chunking
- sparse + dense retrieval
- RRF fusion
- evidence packaging and citation mapping
- grounded generation
- structured citation schema
- degraded response and abstention
- trace recording

Disabled by default:

- planner/query decomposition
- semantic chunking
- reranking
- full temporal scoring
- web fallback
- internal model retrieval
- critic loop

### 7.2 Enterprise Tier

Enterprise improves retrieval precision.

Everything in Standard, plus:

- planner for eligible queries
- temporal and freshness scoring
- reranking
- stronger evidence selection
- semantic chunking as a controlled upgrade path

Still disabled by default:

- external web fallback
- internal model retrieval as the normal path
- full critic loop

### 7.3 Critical Tier

Critical is the high-assurance mode for legal, medical, compliance, and other
high-stakes scenarios.

Everything in Enterprise, plus:

- planner available for high-risk or complex queries
- corrective RAG with allowlisted web fallback
- internal model retrieval for selected corpora
- verification loop
- FreshPrompt conflict-resolution strategy
- strongest degraded behavior
- async path for long-running verified queries

### 7.4 Capability-to-tier matrix

| Capability | Standard | Enterprise | Critical |
|---|---|---|---|
| Metadata enrichment | Yes | Yes | Yes |
| Deterministic chunking | Yes | Yes | Yes |
| Semantic chunking | No default | Feature-flagged | Allowed |
| Namespace isolation | Yes | Yes | Yes |
| Query planning and transformation | No default | Yes for eligible queries | Yes |
| Hybrid retrieval with RRF | Yes | Yes | Yes |
| Temporal and freshness scoring | Minimal or none | Yes | Yes |
| Reranking | No | Yes | Yes |
| Internal model retrieval | No | No default | Yes |
| Corrective RAG | No | No | Yes |
| Evidence packaging and citation mapping | Yes | Yes | Yes |
| Grounded generation | Yes | Yes | Yes |
| Verification loop | No | Lightweight only if later approved | Yes |
| FreshPrompt strategy | No | No | Yes |
| Structured citation schema | Yes | Yes | Yes |
| Degraded response and abstention | Yes | Yes | Yes |
| Trace, audit, and evaluation | Yes | Yes | Yes |

---

## 9. Data Ownership and Policy Model

### Tenant

Top-level customer boundary.

Now describes:

- subscription plan
- maximum execution tier
- default policy
- retention

### Namespace

Tenant-scoped dataset boundary.

Now describes:

- domain
- sensitivity
- freshness profile
- minimum required tier
- web fallback policy
- internal model retrieval policy

### Document

Uploaded file stored under a namespace.

Documents inherit tenant and namespace ownership. They do not permanently belong
to Standard, Enterprise, or Critical.

---

## 10. Product Flow Implications

The intended product journey is:

1. create or join organization
2. open workspace
3. create dataset
4. upload data
5. ingest and monitor readiness
6. create agent
7. open conversation inside that agent
8. choose mode or leave on Auto
9. receive grounded answer with citations and run details

This means future backend work should treat:

- datasets as the source of truth
- agents as behavior attached to datasets
- conversations as history inside agents
- runs as answer-level execution records

---

## 11. API and Schema Implications

The backend now applies these schema and contract rules:

- `subscription_plan` is the billing and entitlement concept
- `max_execution_tier` is the routing ceiling for a tenant
- namespace policy is explicit in schema
- traces record routing fields directly
- API responses should distinguish:
  - requested tier
  - tier used
  - why the tier was chosen

Future schema additions should include:

- workspace model
- agent model
- conversation model
- message model
- run model or run view on top of query traces

---

## 12. Phase 0 Alignment Results

The architecture-driven Phase 0 follow-ups are now in place:

- tenants now store:
  - `subscription_plan`
  - `max_execution_tier`
- namespaces now carry explicit policy fields
- query traces now support routing-specific metadata
- README and core docs now match the final architecture vocabulary

The remaining work now continues from Phase 1 into the product-shell and higher
tier phases.

---

## 13. Design Principles

1. Keep subscription plans and execution tiers separate.
2. Keep user-facing modes separate from internal tiers.
3. Treat datasets as the source of truth.
4. Treat namespace policy as the safety floor.
5. Use auto-routing by default.
6. Allow manual override only within entitlement limits.
7. Never silently downgrade below the required safety level.
8. Keep Standard strong, narrow, and dependable.
9. Gate advanced behavior behind evaluation and policy.
10. Make every important decision traceable.
11. Keep source-policy decisions explicit and auditable.
