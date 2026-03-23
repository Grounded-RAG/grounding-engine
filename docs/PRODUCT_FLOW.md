# Grounded Product Flow

## 1. Why This Document Exists

This document explains Grounded as a **product**, not only as a backend RAG
pipeline.

It captures the user journey we want the platform to grow into:

- organization
- workspace
- dataset
- agent
- conversation
- grounded run

It also clarifies how user-facing **modes** relate to internal execution
**tiers**.

This document should be read together with:

- `docs/SOLUTION_ARCHITECTURE.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/STANDARD_TIER_PHASE1.md`

---

## 2. Product Promise

Grounded should feel like a premium document-intelligence workspace.

Users should be able to:

1. create or join an organization
2. open a workspace
3. create datasets
4. upload documents into those datasets
5. create agents on top of one or more datasets
6. chat with those agents
7. inspect citations, confidence, and traceability
8. manage access, API keys, policies, and usage

The core value is not just "talk to an AI."

The core value is:

- bring your own data
- keep it isolated and governed
- query it through grounded agents
- choose the right depth of reasoning for the job
- inspect why the answer should be trusted

---

## 3. Core Product Objects

### Organization

Top-level customer boundary.

Owns:

- billing plan
- members
- API keys
- workspaces
- usage limits
- governance defaults

### Workspace

A project area inside an organization.

Good for separating:

- teams
- use cases
- environments
- clients or projects

### Dataset

A collection of uploaded documents plus ingestion and retrieval policy.

Owns:

- uploaded files
- ingestion status
- freshness profile
- sensitivity
- minimum required execution tier
- allowed fallback behavior

### Agent

A reusable assistant configured on top of one or more datasets.

Owns:

- name
- description
- system instructions
- attached datasets
- default mode
- allowed modes
- optional tags and use case metadata

### Conversation

A single chat thread inside an agent.

Owns:

- title
- created_by
- created_at
- updated_at
- message history
- last used mode

### Run

The execution record behind one assistant answer.

Owns:

- user query
- selected mode
- effective execution tier
- datasets used
- citations
- confidence
- degraded reasons
- trace id
- timing and usage metadata

### API Key

Programmatic access credential.

Owns:

- organization/tenant binding
- label
- permissions or scope
- auditability

---

## 4. User-Facing Modes vs Internal Tiers

Grounded should keep three layers separate:

### Subscription plans

- Free
- Pro
- Business
- Enterprise

These are commercial entitlements.

### User-facing modes

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

These are product UX labels shown in the chat or agent UI.

### Internal execution tiers

- `Standard`
- `Enterprise`
- `Critical`

These are backend runtime tiers.

### Recommended mapping

| User-facing mode | Typical internal tier | Purpose |
|---|---|---|
| Auto | Routed dynamically | Default experience |
| Instant | Standard | Fast everyday grounded answers |
| Thinking | Enterprise | Better retrieval precision for harder questions |
| Verified | Critical | Highest-assurance path for sensitive work |

### Important rule

Do not expose internal execution-tier names as the main UX control if a better
mode label exists.

Users should think in terms of:

- speed
- depth
- assurance

not in terms of backend routing vocabulary.

---

## 5. Plan Entitlements

The product should gate modes and usage by subscription plan.

| Plan | Auto | Instant | Thinking | Verified | Notes |
|---|---|---|---|---|---|
| Free | Yes | Yes | No | No | Low quotas, baseline access |
| Pro | Yes | Yes | Yes | No | Better usage, deeper mode available |
| Business | Yes | Yes | Yes | Policy-limited | Team use, audit controls, limited verified access |
| Enterprise | Yes | Yes | Yes | Yes | Full controls, compliance, higher quotas |

The product should also track:

- upload quotas
- storage quotas
- query quotas
- mode-specific usage caps

This should feel familiar to users who already understand products like
ChatGPT, Codex, or Claude.

---

## 6. The Ideal User Journey

### Step 1. Sign in or join the organization

The user:

- signs in
- joins an existing organization or creates one
- lands in a workspace

### Step 2. Open the dashboard

The dashboard should show:

- datasets
- ingestion jobs
- agents
- recent conversations
- usage summary
- quick actions

### Step 3. Create a dataset

The user:

- creates a dataset
- names it
- optionally adds a description
- uploads documents
- sees ingestion progress and readiness

### Step 4. Build an agent

The user:

- creates an agent
- attaches one or more datasets
- writes instructions
- chooses a default mode
- optionally restricts or recommends modes

### Step 5. Chat with the agent

The user:

- opens the agent
- starts a new chat
- asks questions
- switches between modes when allowed

### Step 6. Inspect the answer

Every answer should clearly show:

- answer text
- citations
- source snippets
- confidence
- degraded reasons when applicable
- trace id
- mode used
- datasets consulted

### Step 7. Manage the workspace

The user manages:

- datasets
- agents
- API keys
- team members
- plan usage
- governance settings

---

## 7. Product Flow Diagram

```text
Organization
  -> Workspace
    -> Dataset
      -> Upload
      -> Ingest
      -> Ready
    -> Agent
      -> New Chat
      -> Conversation History
      -> Ask Question
      -> Select Mode
      -> Grounded Run
      -> Answer + Citations + Trace
```

---

## 8. How Routing Should Work

### Dataset sets the safety floor

Each dataset should define policy such as:

- sensitivity
- freshness profile
- minimum required tier
- whether external fallback is allowed

### Agent sets the default behavior

Each agent should define:

- attached datasets
- instructions
- default mode
- allowed modes

### Query decides the final runtime depth

At query time the system should consider:

- dataset minimum tier
- agent default mode
- user-selected mode
- router recommendation
- plan entitlement

### Effective tier rule

```text
effective_tier = highest safe requirement among:
  - dataset minimum tier
  - agent default tier
  - router recommendation
  - user-selected mode

then enforce plan entitlement
```

### Safety rule

The system must never silently run a weaker tier than what safety requires.

If the required tier is higher than what the plan allows, fail clearly.

---

## 9. Great Product Behaviors

To feel truly premium and trustworthy, the product should include:

- clear answer inspection
- dataset health visibility
- ingestion monitoring
- conversation history
- run history
- traceability
- mode recommendations
- strong empty states
- auditability
- feedback capture for future evaluation

These are the product behaviors that make Grounded feel more like a serious
platform and less like a demo chatbot.

---

## 10. Current Backend Mapping

The product model above is the target experience.

The backend today already maps to parts of it:

| Product object | Current backend object |
|---|---|
| Organization | Tenant |
| Dataset | Namespace |
| Uploaded file | Document |
| Ingestion progress | IngestionJob |
| Query run / audit | QueryTrace |

What does **not** exist yet as a first-class backend object:

- Workspace
- Agent
- Conversation
- Message
- Run as a separate product object

The current backend already supports the core Standard flow:

- upload
- ingest
- query
- cite
- trace

That makes it a strong foundation for the fuller product shell.

The concrete backend-first build order for that product shell is documented in:

- `docs/PHASE_1_5_BACKEND_PLAN.md`

---

## 11. What Should Exist in the UI

### Public product surface

- Homepage
- Pricing
- Docs / API
- Sign in / create organization

### Logged-in app

- Dashboard
- Dataset page
- Upload flow
- Agent page
- Chat page
- Settings and API keys
- Usage and governance

### Agent chat layout

- left: chats and navigation
- center: conversation
- right: citations, sources, run details

This is the recommended shape for a Contextual-like experience that still fits
Grounded's own system design.

---

## 12. Design Principles

1. Keep plans, modes, and execution tiers separate.
2. Make datasets the source of truth.
3. Put agents on top of datasets, not instead of datasets.
4. Let chats live inside agents.
5. Make mode selection user-friendly and familiar.
6. Preserve backend safety rules behind the UX.
7. Show why an answer should be trusted.
8. Make every important run inspectable.
9. Favor strong defaults over too many controls.
10. Grow product surface without weakening the Standard baseline.
