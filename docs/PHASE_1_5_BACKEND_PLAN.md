# Phase 1.5 Backend Plan

**Status:** implemented on 2026-03-23  
**Current use:** this document is now the historical delivery plan and reference
contract for the implemented product-shell backend.

## Purpose

This document turns the current architecture into a concrete backend delivery
plan for the next stage of Grounded.

Phase 1 already delivered the working **Standard** engine:

- upload
- ingestion jobs
- extraction
- deterministic chunking
- dense indexing
- sparse indexing
- hybrid retrieval
- grounded generation
- structured citations
- degraded responses
- query traces

Phase 1.5 was the next backend step after Phase 1, and it is now complete.

Its job is to turn that Standard engine into a real **product shell** built
around datasets, agents, chats, runs, API keys, and dashboard-ready APIs.

This phase is intentionally **backend-first**. The goal is to make the frontend
fully buildable without pretending that Enterprise and Critical execution logic
already exists.

---

## 1. What Is Already Implemented

The current backend already supports:

- tenant and namespace isolation
- API-key authentication
- document upload
- ingestion job polling
- automatic Standard ingestion
- Standard query execution
- citations and degraded responses
- query trace persistence

Current protected endpoints:

- `GET /v1/auth/smoke`
- `POST /v1/documents/upload`
- `GET /v1/ingestion-jobs/{job_id}`
- `POST /v1/query`

Current backend object model:

- `Tenant`
- `Namespace`
- `Document`
- `IngestionJob`
- `QueryTrace`
- `APIKey`

---

## 2. What Phase 1.5 Was Missing At The Start

The product model is now clearer than the backend model.

We want the product to feel like:

- organization
- workspace
- dataset
- agent
- conversation
- run

But those product objects do not all exist in the backend yet.

The main missing backend pieces are:

- workspace model
- dataset product APIs
- agent model
- conversation and message persistence
- run history APIs
- user-facing mode and capability APIs
- dashboard summary APIs
- API key management APIs
- agent chat endpoint built on top of the current Standard engine

---

## 3. Phase 1.5 Design Rules

These rules should stay fixed during Phase 1.5:

1. Keep the current Standard engine as the execution core.
2. Do not fake Enterprise or Critical behavior before those phases exist.
3. Expose product-facing **modes** separately from backend **tiers**.
4. Keep `Namespace` as the current internal dataset storage model.
5. Expose a product-facing **Dataset** API on top of `Namespace`.
6. Reuse `QueryTrace` as the basis for product-facing **Run** history whenever
   possible.
7. Make `Auto` and `Instant` work now.
8. Show `Thinking` and `Verified` as disabled or coming soon until later
   phases.

---

## 4. Mode Model for Phase 1.5

### User-facing modes

- `auto`
- `instant`
- `thinking`
- `verified`

### Internal execution tiers

- `standard`
- `enterprise`
- `critical`

### Phase 1.5 runtime mapping

| User-facing mode | Phase 1.5 backend behavior |
|---|---|
| `auto` | route to Standard |
| `instant` | route to Standard |
| `thinking` | disabled with clear "coming soon" response |
| `verified` | disabled with clear "coming soon" response |

### Important rule

Even in Phase 1.5, the system must still respect:

- dataset minimum tier
- plan entitlement
- namespace or dataset safety rules

The system must never silently run below the required safe level.

---

## 5. Recommended Delivery Order

This is the backend implementation order that best fits the current system.

### Step 1. Add product-facing mode and capabilities support

Goal:

- let the frontend know what is enabled now and what is coming soon

Add:

- product-facing mode enum
- capability schemas
- mode-to-tier mapping helper
- `GET /v1/capabilities`

Response should describe:

- subscription plan
- enabled modes
- disabled modes
- enabled product features
- coming-soon features

Phase 1.5 expectation:

- `auto`: enabled
- `instant`: enabled
- `thinking`: disabled
- `verified`: disabled

Tests:

- unit tests for mode mapping
- API contract test for capability response

Exit criteria:

- frontend can render available and unavailable modes from one endpoint

### Step 2. Add workspace model

Goal:

- support a real app shell and grouping boundary inside a tenant

Add:

- `Workspace` model
- tenant-to-workspace relationship
- workspace schemas and CRUD endpoints

Recommended endpoints:

- `POST /v1/workspaces`
- `GET /v1/workspaces`
- `GET /v1/workspaces/{workspace_id}`
- `PATCH /v1/workspaces/{workspace_id}`

Tests:

- migration test
- tenant-scoped workspace CRUD tests

Exit criteria:

- datasets and agents can belong to a workspace

### Step 3. Add dataset product APIs on top of Namespace

Goal:

- expose product-facing datasets without rewriting the current namespace-based
  Standard engine

Important implementation rule:

- keep `Namespace` as the storage model for now
- expose `Dataset` in the API layer

Recommended endpoints:

- `POST /v1/datasets`
- `GET /v1/datasets`
- `GET /v1/datasets/{dataset_id}`
- `PATCH /v1/datasets/{dataset_id}`
- `GET /v1/datasets/{dataset_id}/documents`
- `GET /v1/datasets/{dataset_id}/ingestion-jobs`
- `POST /v1/datasets/{dataset_id}/upload`

Tests:

- dataset CRUD tests
- dataset-to-namespace mapping tests
- upload-through-dataset integration test

Exit criteria:

- frontend never needs to think in raw namespace terms

### Step 4. Add agent model and agent-dataset relationship

Goal:

- support reusable assistants built on top of one or more datasets

Add:

- `Agent` model
- `AgentDataset` join table
- default mode
- allowed modes
- status fields

Recommended endpoints:

- `POST /v1/agents`
- `GET /v1/agents`
- `GET /v1/agents/{agent_id}`
- `PATCH /v1/agents/{agent_id}`
- `DELETE /v1/agents/{agent_id}`
- `POST /v1/agents/{agent_id}/datasets`
- `DELETE /v1/agents/{agent_id}/datasets/{dataset_id}`

Tests:

- migration tests
- agent CRUD tests
- dataset attachment validation

Exit criteria:

- one workspace can own reusable agents with attached datasets

### Step 5. Add conversation model

Goal:

- support New Chat and chat history inside one agent

Add:

- `Conversation` model
- title generation or title storage
- last-used mode field

Recommended endpoints:

- `POST /v1/agents/{agent_id}/conversations`
- `GET /v1/agents/{agent_id}/conversations`
- `GET /v1/conversations/{conversation_id}`
- `PATCH /v1/conversations/{conversation_id}`

Tests:

- conversation CRUD tests
- tenant and workspace scoping tests

Exit criteria:

- one agent can contain many chat threads

### Step 6. Add message model

Goal:

- persist chat turns cleanly

Add:

- `Message` model
- role field
- content field
- optional `run_id` for assistant messages

Recommended endpoints:

- `GET /v1/conversations/{conversation_id}/messages`

Tests:

- message persistence tests
- conversation-history retrieval tests

Exit criteria:

- every conversation has durable message history

### Step 7. Add run history on top of QueryTrace

Goal:

- expose product-facing answer inspection without duplicating existing runtime
  truth

Best-practice recommendation:

- reuse `QueryTrace` as the execution backbone
- add only the missing product-facing fields needed for agent and conversation
  history

Recommended endpoints:

- `GET /v1/runs`
- `GET /v1/runs/{run_id}`

Recommended run fields:

- selected mode
- effective tier
- agent id
- conversation id
- datasets used
- citations
- confidence
- degraded reasons
- trace id
- latency and timestamps

Tests:

- run history read tests
- query-trace to run-shape mapping tests

Exit criteria:

- the UI can inspect why an answer was produced and what supported it

### Step 8. Add agent chat endpoint powered by Standard

Goal:

- make the future chat product work now using the current Standard engine

Recommended endpoint:

- `POST /v1/agents/{agent_id}/chat`

Request should include:

- `conversation_id`
- `message`
- `mode`

Backend behavior:

- resolve the agent
- resolve attached datasets
- validate mode availability
- map `auto` and `instant` to Standard
- reject `thinking` and `verified` with clear coming-soon behavior
- run the current grounded query path
- persist:
  - user message
  - assistant message
  - run metadata

Tests:

- end-to-end agent chat test
- message persistence test
- disabled-mode contract test

Exit criteria:

- agent chat works on top of the current Standard engine

### Step 9. Add dashboard summary endpoints

Goal:

- support a real product dashboard

Recommended endpoints:

- `GET /v1/dashboard/summary`
- `GET /v1/dashboard/recent-runs`
- `GET /v1/dashboard/recent-jobs`

Recommended summary fields:

- dataset count
- document count
- indexed documents
- running jobs
- failed jobs
- agent count
- conversation count
- recent runs

Tests:

- dashboard aggregation tests

Exit criteria:

- frontend can render a useful dashboard without stitching many unrelated calls

### Step 10. Add API key management endpoints

Goal:

- support developer integrations and settings pages

Recommended endpoints:

- `GET /v1/api-keys`
- `POST /v1/api-keys`
- `POST /v1/api-keys/{key_id}/revoke`

Recommended fields:

- label
- created_at
- last_used_at
- revoked_at

Tests:

- API key creation tests
- revocation tests
- auth behavior after revoke

Exit criteria:

- the product can manage integration credentials from the UI

### Step 11. Harden Standard for product-shell use

Goal:

- make the backend advisor-ready and frontend-ready

Add:

- broader integration coverage for the new product APIs
- stable demo seed data
- example payloads
- smoke scripts for:
  - create dataset
  - upload
  - create agent
  - start conversation
  - chat in `auto`
  - inspect run
- clear disabled-mode behavior for `thinking` and `verified`

Tests:

- end-to-end product-shell smoke tests
- regression suite over the Standard engine

Exit criteria:

- the backend can support a presentable product shell without mock backend
  behavior

---

## 6. What Should Be Live After Phase 1.5

The backend should support these real product flows:

- create workspace
- create dataset
- upload documents into a dataset
- monitor ingestion
- create agent
- attach datasets to an agent
- start new chat
- continue chat history
- chat in `auto`
- chat in `instant`
- inspect citations and run details
- manage API keys
- view dashboard summary

---

## 7. What Should Still Be Marked Coming Soon

The backend can expose these in capabilities, but they should remain disabled:

- `thinking` mode
- `verified` mode
- Enterprise planner logic
- temporal scoring
- reranking
- semantic chunking upgrade path
- verification loop
- corrective retrieval
- internal model retrieval

This keeps the product honest while still letting the UI show the full product
shape.

---

## 8. Recommended Testing Strategy

For every Phase 1.5 step, add:

- migration coverage if schema changes are introduced
- unit tests for mapping and policy logic
- integration tests for API contracts
- tenant-isolation tests for every new product object

Before Phase 1.5 is considered complete, run:

- compile check
- migration smoke
- full backend test suite
- live source-run smoke for:
  - workspace
  - dataset
  - upload
  - agent chat
  - run inspection

---

## 9. Definition of Done

Phase 1.5 is complete when:

1. the backend exposes datasets, agents, conversations, and runs as first-class
   product APIs
2. `auto` and `instant` work through an agent chat flow
3. `thinking` and `verified` are visible but clearly unavailable
4. dashboard and API key management endpoints exist
5. the Standard engine still remains the real execution path underneath
6. the frontend team can build the full product shell without inventing missing
   backend contracts

---

## 10. What Comes After Phase 1.5

After the product shell is in place:

- Phase 2 turns on `thinking` by adding Enterprise retrieval upgrades
- Phase 3 turns on `verified` by adding Critical assurance features

That keeps Grounded's sequence clean:

1. working Standard engine
2. product shell on top of Standard
3. Enterprise depth
4. Critical assurance
