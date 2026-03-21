# Grounded Team Brief

## What Grounded Is

Grounded is a platform where users upload their own documents and ask questions
over that data. The system ingests the documents, indexes them, retrieves
evidence, and returns grounded answers with citations.

The goal is not just "build a chatbot." The goal is to build a trustworthy RAG
platform that is stronger than a normal demo-style RAG system.

## The Big Idea

Grounded separates three things that are easy to confuse:

- **subscription plans**: what the customer pays for
- **execution tiers**: how deeply the system processes a query
- **namespace policy**: rules attached to a dataset or workspace

This is important because the same customer may need different processing depth
for different queries, even on the same dataset.

## Plans vs Tiers

### Subscription plans

These are product and billing concepts:

- Free Plan
- Pro Plan
- Business Plan
- Enterprise Plan

They control:

- quotas
- storage
- which execution tiers are allowed
- whether manual override is allowed

### Execution tiers

These are runtime processing modes:

- Standard Tier
- Enterprise Tier
- Critical Tier

They control:

- whether planner logic runs
- whether reranking runs
- whether verification loops run
- whether corrective web fallback is allowed

## What Each Tier Means

### Standard Tier

This is the first strong production baseline.

It includes:

- tenant and namespace isolation
- deterministic chunking
- hybrid retrieval
- RRF fusion
- evidence packaging
- grounded generation
- structured citations
- degraded responses instead of bluffing
- traces

It does **not** include by default:

- planner
- semantic chunking
- reranking
- CRAG web fallback
- internal model retrieval
- critic loop

### Enterprise Tier

This improves retrieval precision.

It adds:

- planner for eligible complex queries
- temporal scoring
- reranking
- stronger evidence selection
- semantic chunking as a controlled upgrade

### Critical Tier

This is the highest-assurance path.

It adds:

- critic/verification loop
- CRAG-style corrective fallback
- internal model retrieval for selected corpora
- FreshPrompt-style conflict handling
- strongest degraded behavior
- async path for long-running verified queries

## Why We Build Standard First

Standard is the narrowest solid product slice.

It is enough to prove that Grounded can:

- ingest documents
- retrieve evidence using sparse and dense search
- answer with citations
- stay tenant-safe
- return honest degraded responses when needed

If Standard is not strong, adding Enterprise and Critical features later will
only create complexity on top of a weak baseline.

## How Data and Tier Selection Work

### Upload-time

When data is uploaded, it is assigned to:

- a tenant
- a namespace
- a domain and sensitivity profile
- a minimum required tier

This creates the policy guardrails.

### Query-time

When a query comes in, the system decides the execution tier using:

- namespace minimum tier
- router recommendation
- user-requested tier, if allowed
- plan entitlement limits

So:

- **data belongs to tenant + namespace**
- **queries are routed to a tier**

## Why Grounded Is Better Than Normal RAG

Basic RAG often means:

- chunk
- embed
- vector search
- answer

Grounded Standard is stronger because it adds:

- multitenant isolation
- hybrid retrieval
- evidence packaging
- structured citations
- degraded behavior
- traceability

Grounded Enterprise and Critical go further by adding stronger retrieval quality
and stronger verification.

## Delivery Shape

### Phase 0

Backend foundation:

- auth
- tenancy
- storage
- health/readiness
- schema
- logging
- tracing
- CI/tests

### Phase 0.5

Architecture and docs alignment:

- plans vs tiers
- tier routing
- capability model
- Phase 0 alignment fixes against the final design

### Phase 1

Standard Tier:

- upload
- extraction
- metadata enrichment
- deterministic chunking
- sparse + dense retrieval
- RRF fusion
- evidence packaging
- grounded generation
- structured citations
- traces

### Phase 2

Enterprise Tier:

- planner for eligible queries
- temporal scoring
- reranking
- semantic chunking experiment

### Phase 3

Critical Tier:

- verification loop
- CRAG web fallback
- internal model retrieval
- FreshPrompt
- async verified query path

## What Is Intentionally Postponed

These are not part of the first strong baseline:

- planner by default in Standard
- semantic chunking as the default chunker
- web fallback outside Critical
- internal model retrieval as the main retrieval path
- critic loop in lower tiers

This is intentional. The system should not get heavy before the baseline is
stable.
