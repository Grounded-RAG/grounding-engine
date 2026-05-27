## 1. Executive Summary

Grounded AI is a multitenant, reliability-first Retrieval-Augmented Generation (RAG) platform for user-owned knowledge. The system enables organizations to upload documents into governed datasets, index those documents through a structured ingestion pipeline, attach datasets to reusable grounded agents, and query them through a web dashboard or API. Every answer is produced from tenant-scoped evidence, returned with citations, confidence signals, verification status, and a persisted run trace for inspection and audit.

The platform is designed around two core rules:

- data belongs to a tenant and namespace-bound dataset
- queries are routed to an effective execution tier

Grounded AI separates commercial subscription plans, product-facing usage modes, internal execution tiers, dataset policies, and runtime routing decisions. This separation allows the system to remain fast for straightforward questions while applying deeper retrieval, temporal scoring, reranking, and verification for more demanding queries.

The delivered system includes:

- a React dashboard for onboarding, dataset management, agent creation, chat, run inspection, and API key administration
- a FastAPI backend exposing tenant-scoped product and query APIs
- a PostgreSQL operational database and sparse retrieval index
- a Qdrant vector index for dense retrieval
- object storage for canonical documents and ingestion artifacts
- a hybrid retrieval and grounded generation pipeline with evidence packaging, structured citations, degraded honesty, and trace persistence

## 2. Problem Overview

### 2.1 Problem Statement

Organizations increasingly rely on internal documents such as policies, manuals, research notes, specifications, and operational records. Traditional keyword search often fails to capture semantic intent, while basic RAG systems frequently produce unverified or weakly grounded answers. Common weaknesses include:

- weak evidence retrieval for ambiguous or multi-part questions
- hallucinated answers when support is incomplete
- poor multitenant isolation and data governance
- limited traceability of how an answer was produced
- inability to adapt processing depth to query complexity and dataset sensitivity

### 2.2 Research Motivation

The system is motivated by the need for trustworthy document intelligence rather than generic conversational AI. The project explores how a managed RAG platform can improve practical reliability by combining:

- structured ingestion
- deterministic chunking
- hybrid retrieval
- execution-tier routing
- evidence-first answer generation
- verification and degraded response behavior
- auditable traces and citations

### 2.3 System Purpose

The purpose of Grounded AI is to provide a dependable knowledge access layer over user-owned documents. Instead of requiring each organization to build its own ingestion, indexing, routing, retrieval, citation, and trust stack, the platform offers these capabilities as a single integrated product.

### 2.4 Target Users

The system serves:

- organizations managing internal knowledge and document-heavy workflows
- technical teams querying documentation and specifications
- compliance and policy teams requiring traceable answers
- research and analysis teams working with curated corpora
- developers integrating grounded retrieval through APIs
- operators and administrators managing datasets, agents, API keys, and runs

### 2.5 Project Goals

The project goals are to:

- provide grounded answers over user-owned data
- preserve hard tenant and dataset isolation
- support both dashboard and API access patterns
- expose citations, confidence, and traceability for every answer
- route queries through the appropriate execution depth
- support reusable grounded agents over one or more datasets
- maintain ingestion, retrieval, and run observability within the product shell

### 2.6 Benefits of the System

The system provides the following benefits:

- more reliable answers than basic vector-only RAG
- auditable grounded responses with explicit evidence references
- honest degraded behavior when support is insufficient
- structured tenant and workspace organization
- reusable datasets and agents for repeated use cases
- unified operational visibility across ingestion, retrieval, and run history

### 2.7 End-to-End Objectives

Grounded AI is designed to:

- ingest supported source documents such as TXT, PDF, and DOCX
- extract and normalize text with metadata enrichment
- create deterministic chunk manifests and hybrid indexes
- support dataset and agent lifecycle management
- process grounded queries through Standard, Enterprise, and Critical execution tiers
- generate answers with citations and trust metadata
- persist runs for analysis, audit, and evaluation

## 3. System Overview

Grounded AI operates as a managed document-intelligence workspace. The core product model is:

- Organization/Tenant
- Workspace
- Dataset
- Agent
- Conversation
- Run
- API Key

The backend persistence layer maps these concepts as follows:

- `Tenant` stores the organization boundary
- `Workspace` groups product activity
- `Namespace` stores dataset policy and identity
- `Document` stores uploaded source files
- `IngestionJob` tracks ingestion execution
- `DocumentChunkRecord` stores sparse-searchable chunks
- `Agent` stores reusable grounded assistant configuration
- `AgentDataset` links agents to datasets
- `Conversation` stores chat threads
- `Message` stores chat history
- `QueryTrace` stores the execution record for each run

The user-facing mode layer exposes:

- `Auto`
- `Instant`
- `Thinking`
- `Verified`

These map to internal execution behavior:

- `Instant` maps to `Standard`
- `Thinking` maps to `Enterprise`
- `Verified` maps to `Critical`
- `Auto` allows routing logic to choose the best effective tier

The runtime execution tiers are:

- `Standard`: baseline hybrid grounded RAG
- `Enterprise`: stronger planning, temporal scoring, and reranking
- `Critical`: highest-assurance verification and corrective safeguards

## 4. Architecture

### 4.1 Frontend Architecture

**Purpose**

The frontend provides the product shell through which users sign in, create workspaces, manage datasets and agents, upload documents, interact with grounded chat, inspect runs, and manage API keys.

**Components**

- React application bootstrapped through `frontend/src/main.tsx`
- page-based UI under `frontend/src/pages`
- shared UI components built with shadcn-style primitives and Tailwind CSS
- React Query for API state management
- React Router for navigation
- local auth/session context for API key-backed workspace access

**Key UI Pages**

- landing and product marketing page
- login page with email and API key access
- sign-up page
- onboarding workspace wizard
- dashboard page
- datasets list and dataset detail pages
- agents list and agent chat page
- runs inspection page
- settings and API key management page

**Interactions**

- calls FastAPI product endpoints through typed client utilities
- stores current API key and active workspace in frontend auth state
- uses React Query invalidation after create, upload, attach, chat, and revoke actions
- polls ingestion jobs while queued or running

**Technologies**

- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- Framer Motion
- Sonner toast notifications

### 4.2 Backend Architecture

**Purpose**

The backend provides the application API, tenant authentication, product-shell resource management, ingestion orchestration, grounded query execution, and run persistence.

**Components**

- FastAPI application entrypoint in `backend/app/main.py`
- versioned API routers under `backend/app/api/v1`
- SQLAlchemy ORM models under `backend/app/models`
- service layer under `backend/app/services`
- ingestion workers under `backend/app/workers`
- core adapters for database, storage, embeddings, vector search, telemetry, and generators under `backend/app/core`

**Interactions**

- authenticates requests through API keys in `X-API-Key` or Bearer format
- reads and writes tenant-scoped product data in PostgreSQL
- stores source files and derived artifacts in object storage
- indexes dense vectors in Qdrant
- executes grounded query orchestration through service composition

**Technologies**

- FastAPI
- SQLAlchemy Async ORM
- PostgreSQL
- Qdrant
- object storage compatible with S3/MinIO
- Python worker pipeline functions

### 4.3 RAG Architecture

**Purpose**

The RAG architecture converts uploaded documents into searchable evidence and answers user questions using only supported, tenant-authorized data.

**Core Pipeline Layers**

- ingestion and metadata enrichment
- chunking and indexing
- query analysis and routing
- sparse retrieval
- dense retrieval
- Reciprocal Rank Fusion
- tier-aware reranking and temporal scoring
- evidence packaging
- grounded generation
- response shaping and confidence calibration
- verification and degraded honesty
- run trace persistence

**Capabilities by Tier**

- Standard: deterministic chunking, hybrid retrieval, RRF, evidence packaging, grounded generation, citations, degraded responses, trace persistence
- Enterprise: heavier planning, temporal scoring, stronger reranking, richer evidence selection
- Critical: verification loop, contradiction handling, corrective safeguards, strongest degraded behavior

### 4.4 Database Architecture

**Purpose**

The relational database stores tenants, workspaces, datasets, documents, ingestion jobs, agents, conversations, messages, API keys, and query traces.

**Components**

- PostgreSQL operational tables
- enum-backed constraints for plans, tiers, modes, statuses, sensitivity, and freshness
- JSONB fields for policy, citations, traces, token usage, and mode allowlists
- foreign keys enforcing tenant-scoped relationships

**Interactions**

- product APIs perform CRUD and listing over workspace resources
- query pipeline records `QueryTrace`
- retrieval uses PostgreSQL full-text search over `document_chunks`
- dashboard aggregates counts from relational entities

### 4.5 Vector Database Architecture

**Purpose**

The vector database supports dense semantic retrieval over chunk embeddings.

**Components**

- Qdrant collection configured by application settings
- one dense point per chunk
- payload fields carrying tenant, dataset, document, chunk, structural, and source metadata

**Interactions**

- dense indexing writes chunk vectors during ingestion
- retrieval searches Qdrant with query embeddings
- returned points are filtered by tenant and namespace metadata before fusion

### 4.6 API Architecture

**Purpose**

The API architecture exposes authenticated product, ingestion, query, dashboard, and run interfaces under a versioned REST contract.

**Components**

- `/health/*` for liveness and readiness
- `/v1/auth/*` for email preview auth and auth smoke
- `/v1/workspaces` for workspace lifecycle
- `/v1/datasets` for dataset lifecycle and dataset-scoped uploads
- `/v1/documents/*` and `/v1/ingestion-jobs/*` for direct document operations
- `/v1/agents/*` for agent lifecycle and chat
- `/v1/conversations/*` for conversation lifecycle and history
- `/v1/query` for direct dataset query
- `/v1/runs/*` for run inspection
- `/v1/dashboard/*` for workspace summary widgets
- `/v1/api-keys/*` for developer credential management
- `/v1/capabilities` for product and mode availability

### 4.7 Dashboard Architecture

**Purpose**

The dashboard surfaces operational and product activity in a single workspace interface.

**Components**

- workspace welcome hero and quick actions
- summary cards for datasets, agents, runs, and documents
- recent runs view
- recent ingestion jobs view
- mode capability status panel
- dataset readiness and policy panels
- run detail inspector

**Interactions**

- dashboard summary aggregates data from datasets, documents, agents, conversations, and jobs
- run inspection reads persisted `QueryTrace` projections
- recent ingestion jobs combine job and document context

### 4.8 Deployment Architecture

**Purpose**

The deployment architecture packages the application as a service-oriented stack with clearly separated compute and storage dependencies.

**Components**

- frontend web application
- backend API container
- PostgreSQL database
- Redis service for broader platform readiness and asynchronous support
- Qdrant vector database
- MinIO object storage for local and self-hosted operation
- Docker Compose definitions in `docker-compose.yml` and `docker-compose.dev.yml`

**Interactions**

- backend depends on PostgreSQL, storage, and Qdrant
- frontend connects to backend over HTTP
- readiness checks validate configuration, database connectivity, and storage availability

### 4.9 Security Architecture

**Purpose**

The security architecture ensures authenticated access, tenant isolation, scoped data retrieval, and safe operational trace handling.

**Components**

- API key authentication dependency
- hashed API key storage
- tenant-bound resource lookup in every service path
- dataset policy fields controlling tier minimums and fallback allowances
- redacted run persistence
- CORS configuration and request context middleware

**Interactions**

- every API request resolves `TenantContext`
- all critical database queries filter by `tenant_id`
- runs store `query_redacted` and `final_answer_redacted` for audit-safe trace retention

### 4.10 Monitoring Architecture

**Purpose**

The monitoring architecture provides operational awareness across service health, request context, ingestion flow, and query execution traces.

**Components**

- `/health/live`
- `/health/ready`
- structured application logging and request context
- query trace persistence with routing, evidence, latency, and verification metadata
- dashboard recent job and recent run views

**Interactions**

- readiness checks validate database and storage dependencies
- query execution binds trace and tenant context into telemetry
- traces provide the primary observability substrate for answer behavior analysis

## 5. System Workflow

### 5.1 End-to-End Product Workflow

1. User signs in with email credentials or an API key.
2. The system resolves the tenant and active workspace.
3. The user creates a dataset within the workspace.
4. The user uploads one or more documents into the dataset.
5. The ingestion pipeline extracts text, enriches metadata, chunks content, and builds sparse and dense indexes.
6. The user creates an agent and attaches one or more datasets.
7. The user opens a conversation and sends a question.
8. The system resolves dataset scope, mode, and effective execution tier.
9. The retrieval pipeline performs hybrid search and ranking.
10. The evidence packaging layer selects grounded support chunks.
11. The generator produces an evidence-grounded draft answer.
12. Response shaping validates citations, calibrates confidence, and applies degraded honesty where needed.
13. Critical verification logic checks claims against evidence when applicable.
14. The system returns the grounded response with citations, confidence, and verification metadata.
15. The full run is stored as a trace and becomes visible in the dashboard.

### 5.2 Detailed Ingestion Workflow

#### Step 1. Upload reception

The user uploads a supported file through `/v1/datasets/{dataset_id}/upload` or `/v1/documents/upload`.

The upload module:

- validates the filename and extension
- accepts supported formats: `.txt`, `.pdf`, `.docx`
- validates MIME type consistency
- enforces maximum file size
- computes a SHA-256 checksum for duplicate detection

#### Step 2. Tenant and dataset resolution

The system authenticates the API key and verifies that the target dataset belongs to the authenticated tenant.

#### Step 3. Canonical storage

The uploaded file is stored in object storage under a deterministic tenant-scoped path:

- `tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/source/{filename}`

The system creates:

- a `Document` record with status `uploaded`
- an `IngestionJob` record with status `queued`

#### Step 4. Extraction and metadata enrichment

The ingestion worker downloads the canonical object and extracts text according to document type:

- TXT files are decoded as UTF-8
- PDF files are parsed with page text extraction and metadata inspection
- DOCX files are parsed through paragraph extraction and core properties

The extraction layer normalizes line endings, removes invalid null characters, trims whitespace, and stores normalized text as an artifact. It also enriches metadata such as:

- title
- published or created timestamp when available
- character count

#### Step 5. Deterministic chunking

The normalized text is transformed into a chunk manifest using token-aware deterministic chunking. The manifest records:

- chunk IDs
- chunk index
- chunk text
- section title and section slug when derived
- chunk role
- token and character spans
- heading and list structure hints

The manifest is stored as a reusable ingestion artifact.

#### Step 6. Sparse indexing

Chunk content is materialized into PostgreSQL `document_chunks`. Each row includes a computed `tsvector` search index for lexical retrieval.

#### Step 7. Dense embedding generation

Each chunk is converted into an embedding input enriched with light structural context such as document title, section title, and chunk role.

#### Step 8. Vector indexing

The resulting embeddings are upserted into Qdrant as tenant- and dataset-scoped points. Each vector payload carries retrieval metadata required at query time.

#### Step 9. Completion

After indexing succeeds:

- the `Document` status becomes `indexed`
- the `IngestionJob` status becomes `indexed`

If a failure occurs, both the job and document are marked accordingly with persisted error metadata.

### 5.3 Detailed Query Workflow

#### Step 1. Query submission

The user submits a question either:

- directly to `/v1/query` against a dataset
- through `/v1/agents/{agent_id}/chat` inside an agent conversation

#### Step 2. Authentication and scope resolution

The backend authenticates the API key, resolves the tenant, verifies dataset ownership, and optionally verifies the agent-conversation binding.

#### Step 3. Conversation context and query analysis

The query service analyzes the user request and may build a query plan that considers:

- query type
- ambiguity
- comparison or action intent
- attribute terms
- conversation carryover
- retrieval rewrites or expansions

Small-talk and filler prompts are intercepted early and converted into scoped clarification responses instead of wasting retrieval resources.

#### Step 4. Execution-tier routing

The system determines the effective execution tier by combining:

- explicit `requested_tier` if present
- selected user-facing mode
- auto-router recommendation
- dataset minimum tier policy
- tenant entitlement ceiling

The system records:

- requested tier
- router recommendation
- effective tier
- routing reason
- request source

#### Step 5. Hybrid retrieval

The retrieval stage performs:

- sparse retrieval in PostgreSQL full-text search
- dense retrieval in Qdrant using query embeddings

Each path returns ranked chunk candidates restricted by tenant and dataset scope.

#### Step 6. Reciprocal Rank Fusion

Sparse and dense candidates are merged into a single fused candidate set using Reciprocal Rank Fusion. This improves robustness by combining lexical exactness with semantic similarity.

#### Step 7. Query-aware reranking

The fused candidates are rescored using retrieval heuristics that account for:

- query term coverage
- section alignment
- chunk role relevance
- list and heading structure
- intent-specific support patterns

Enterprise routing applies stronger reranking and structured support clustering.

#### Step 8. Temporal scoring

When the dataset freshness profile and query intent require recency, the system boosts newer supporting documents. This is especially important for update-sensitive questions.

#### Step 9. Evidence packaging

The top fused candidates are transformed into an evidence package. The packaging logic:

- selects the most answer-bearing support cluster
- limits evidence volume to a compact grounded set
- assigns stable citation IDs such as `E001`
- preserves chunk, section, and document metadata

The evidence package becomes the sole support boundary for grounded generation.

#### Step 10. Grounded generation

The generation service selects the configured backend and produces a structured grounded answer draft. Supported generation backends include:

- local grounded generator
- Gemini-backed generator
- OpenAI-compatible generator

The draft includes:

- answer text
- cited evidence IDs
- snippet map per citation
- support coverage metadata
- source diversity metadata
- generator provider identifier

#### Step 11. Citation contract validation

The generation layer validates that:

- cited chunk IDs exist in the evidence package
- citation snippets exactly align with cited evidence
- refusal drafts follow strict unsupported-answer behavior when required
- answer structure matches query intent patterns

#### Step 12. Response shaping

The validated draft is converted into the API response schema. This stage:

- normalizes citation quotes
- computes confidence score
- derives confidence label
- derives support summary
- sets verification status
- adds degraded reasons if support is weak or ambiguous

#### Step 13. Critical verification

For Critical execution, the system verifies the shaped response against selected evidence by:

- splitting the answer into auditable claims
- checking claim-term support across evidence chunks
- detecting contradiction patterns
- classifying claims as supported, partially supported, or unsupported
- producing accept, degrade, or refuse decisions

#### Step 14. Grounded response return

The final response returned to the client contains:

- answer text
- citations
- confidence score and label
- support summary
- verification status
- degraded reasons
- provider metadata

#### Step 15. Run trace persistence

The query service persists a `QueryTrace` that stores:

- query text in redacted form
- selected mode and tier routing
- retrieved chunk IDs
- selected evidence IDs
- citations
- confidence
- degraded reasons
- verifier result
- stage latencies
- token usage
- final answer text in redacted form

This trace powers the run history and audit interface.

## 6. Feature Explanation

### 6.1 Multitenant Workspace Model

The platform organizes all resources under tenant ownership and workspace grouping. This ensures that datasets, agents, API keys, conversations, and runs remain logically isolated and operationally manageable.

### 6.2 Dataset-Centric Knowledge Management

Datasets act as source-of-truth collections. Each dataset carries domain and governance metadata, including sensitivity level, freshness profile, minimum tier requirement, and controlled fallback permissions.

### 6.3 Managed Document Ingestion

The system accepts source files, stores them canonically, extracts text, enriches metadata, chunks content, and indexes both sparse and dense representations through a managed ingestion workflow.

### 6.4 Grounded Agents

Agents are reusable assistants configured on top of one workspace and one or more attached datasets. Each agent stores system instructions, default mode, allowed modes, and lifecycle status.

### 6.5 Mode-Aware Chat Experience

Users interact with agents through friendly product modes:

- Auto
- Instant
- Thinking
- Verified

These convey speed, depth, and assurance while the backend maps them to execution behavior.

### 6.6 Hybrid Retrieval

The retrieval engine combines PostgreSQL full-text search and Qdrant dense similarity search, then fuses the results using Reciprocal Rank Fusion for stronger grounding quality.

### 6.7 Tiered Query Processing

The system adapts execution depth according to query difficulty, dataset policy, and entitlement. Standard handles routine grounded Q&A, Enterprise strengthens retrieval precision, and Critical adds higher-assurance verification.

### 6.8 Structured Citations

Every grounded answer includes structured citations referencing exact evidence chunks. This makes answers inspectable rather than opaque.

### 6.9 Confidence and Trust Signals

The platform attaches confidence scores, labels, support summaries, degraded reasons, verification status, and provider details so users can judge answer reliability.

### 6.10 Run Traceability

Every query execution is persisted as a run, allowing post-hoc inspection of routing, evidence, latency, and output behavior.

## 7. Modules

### 7.1 Authentication Module

**Purpose**

Authenticates API access and resolves the current tenant context.

**Inputs**

- `X-API-Key` header or Bearer token
- email sign-up or sign-in credentials

**Outputs**

- `TenantContext`
- preview auth response with workspace and API key information

**Workflow**

1. Receive API key or email credentials.
2. For API key requests, hash the supplied key and locate the matching `APIKey` record.
3. Load the associated tenant.
4. Reject invalid or revoked keys.
5. Update `last_used_at`.
6. Return tenant and entitlement metadata.

**Internal Logic**

- supports both email preview auth and API key auth
- stores only hashed API keys
- binds tenant context into request telemetry

**Interactions**

- used by all product and query routes
- powers sign-up, sign-in, auth smoke, and developer access

### 7.2 Document Management Module

**Purpose**

Manages persisted uploaded documents and their ingestion linkage.

**Inputs**

- dataset ID
- file payload
- optional title
- reindex request

**Outputs**

- `Document` record
- `IngestionJob` record
- upload or reindex response

**Workflow**

1. Validate dataset ownership.
2. Normalize filename and title.
3. Validate MIME type and size.
4. Compute checksum for duplicate detection.
5. Store canonical source object.
6. Create document and ingestion job records.
7. Optionally schedule background ingestion.

**Internal Logic**

- duplicate uploads resolve to the existing indexed document by checksum
- object keys are deterministic and tenant-scoped
- document status tracks upload, processing, indexed, failed, and archived states

**Interactions**

- feeds the ingestion pipeline
- used by dataset and document upload endpoints

### 7.3 Upload Module

**Purpose**

Accepts source files and initiates ingestion.

**Inputs**

- multipart form file
- dataset or namespace identifier
- optional user-supplied title

**Outputs**

- upload acceptance response with document and job identifiers

**Workflow**

1. Receive multipart upload.
2. Validate supported format.
3. Store source bytes.
4. Create queued ingestion job.
5. Trigger background pipeline when auto-run is enabled.

**Internal Logic**

- supports TXT, PDF, DOCX
- returns `already_exists` when the same bytes already exist in the dataset

**Interactions**

- depends on document service and ingestion workers

### 7.4 Query Processing Module

**Purpose**

Coordinates end-to-end grounded query execution.

**Inputs**

- dataset ID or agent chat request
- query text
- optional selected mode
- optional requested tier
- optional conversation context

**Outputs**

- `GroundedAnswerResponse`
- persisted `QueryTrace`

**Workflow**

1. Validate tenant-scoped dataset access.
2. Build conversation-aware query plan.
3. Resolve execution routing.
4. Perform hybrid retrieval.
5. Package evidence.
6. Generate grounded draft.
7. Shape response.
8. Apply verification when required.
9. Persist trace.

**Internal Logic**

- intercepts small-talk queries and asks for clarification
- maps mode selection into internal tier requests
- supports Auto routing into Enterprise for hard queries

**Interactions**

- uses retrieval, evidence, generation, shaping, and verification modules

### 7.5 Semantic Chunking Module

**Purpose**

Provides the architecture slot for topic-aware chunking improvements above the deterministic baseline.

**Inputs**

- extracted document text
- chunking configuration

**Outputs**

- chunk manifest preserving semantic coherence and structural continuity

**Workflow**

1. Analyze document structure and topic transitions.
2. Preserve section coherence where possible.
3. produce chunk boundaries suitable for retrieval.

**Internal Logic**

- the architecture places semantic chunking as a controlled upgrade path in higher tiers
- the delivered system uses deterministic token-aware chunking as the operational baseline and semantic chunking as part of the overall final capability model

**Interactions**

- feeds both sparse and dense indexing quality

### 7.6 Embedding Module

**Purpose**

Generates dense vector representations for retrieval.

**Inputs**

- retrieval-oriented chunk text
- query text

**Outputs**

- dense embedding vectors

**Workflow**

1. Construct embedding input with structural hints.
2. Call configured embedding backend.
3. Return embeddings for indexing or search.

**Internal Logic**

- enriches embedding text with document title, section title, chunk role, and structure cues

**Interactions**

- used by dense indexing and dense retrieval

### 7.7 Retrieval Module

**Purpose**

Finds relevant candidate chunks for a query.

**Inputs**

- tenant ID
- dataset ID
- query text
- execution tier
- freshness profile

**Outputs**

- sparse hits
- dense hits
- fused hits
- retrieval debug metadata

**Workflow**

1. Execute sparse search in PostgreSQL FTS.
2. Embed the query and execute dense search in Qdrant.
3. Merge results through RRF.
4. Apply query-aware rescoring.
5. Apply temporal scoring where appropriate.

**Internal Logic**

- uses section metadata, intent scoring, and structure-aware bonuses
- respects tenant and dataset isolation on every search path

**Interactions**

- upstream of evidence packaging and downstream of query analysis

### 7.8 Hybrid Search Module

**Purpose**

Combines lexical and semantic retrieval to improve robustness.

**Inputs**

- sparse candidate list
- dense candidate list

**Outputs**

- fused ranked candidate list

**Workflow**

1. Rank sparse hits.
2. Rank dense hits.
3. Apply Reciprocal Rank Fusion.
4. Produce one merged candidate set.

**Internal Logic**

- preserves complementary strengths of exact term matches and semantic similarity

**Interactions**

- serves as the central retrieval merge stage before evidence selection

### 7.9 Reranking Module

**Purpose**

Improves the ordering of fused retrieval candidates.

**Inputs**

- fused retrieved chunks
- query plan
- execution tier

**Outputs**

- reranked chunk list

**Workflow**

1. Score term coverage and answer-bearing signals.
2. Reward section and chunk-role alignment.
3. cluster multi-part support where needed.
4. return tier-aware ranked results.

**Internal Logic**

- applies lightweight heuristics in Standard
- strengthens structured support selection in Enterprise

**Interactions**

- directly affects evidence packaging quality

### 7.10 Temporal Scoring Module

**Purpose**

Prioritizes fresher evidence when the question explicitly depends on recency.

**Inputs**

- fused hits
- dataset freshness profile
- document timestamps
- query plan

**Outputs**

- temporally rescored candidate set

**Workflow**

1. Detect whether the query asks for current or recent information.
2. Load timestamps for candidate documents.
3. Calculate relative freshness ratios.
4. Apply profile-weighted score boosts.

**Internal Logic**

- uses `published_at` or `created_at` as effective freshness timestamps
- applies profile weights for `stable`, `balanced`, and `aggressive`

**Interactions**

- sits between fusion/reranking and evidence packaging

### 7.11 Verification Module

**Purpose**

Checks whether the final answer is sufficiently supported by the selected evidence.

**Inputs**

- shaped grounded response
- evidence package

**Outputs**

- verifier decision
- verified claim records
- contradiction and unsupported-claim metadata

**Workflow**

1. Split the answer into claims.
2. Extract meaningful lexical terms from each claim.
3. Compare claims to evidence chunks.
4. classify support status per claim.
5. detect contradiction signals across chunks.
6. decide accept, degrade, or refuse.

**Internal Logic**

- supports claim-level auditing
- generates retry terms when support is weak

**Interactions**

- integrated into Critical path and persisted in `QueryTrace.verifier_result`

### 7.12 Citation Module

**Purpose**

Attaches exact evidence references to every grounded answer.

**Inputs**

- evidence package
- grounded answer draft with cited chunk IDs and snippets

**Outputs**

- structured `CitationResponse` list

**Workflow**

1. validate cited chunk IDs.
2. validate snippet-to-evidence grounding.
3. assign citation IDs.
4. normalize quote excerpts.

**Internal Logic**

- enforces strict snippet alignment and deduplicates chunk references

**Interactions**

- used in response shaping and run projection

### 7.13 Dashboard Module

**Purpose**

Provides workspace-level operational summaries and recent activity.

**Inputs**

- tenant ID

**Outputs**

- dashboard summary counts
- recent runs list
- recent ingestion jobs list

**Workflow**

1. count datasets, documents, agents, conversations, and jobs.
2. fetch recent runs.
3. fetch recent ingestion jobs with document context.

**Internal Logic**

- aggregates counts through tenant-scoped SQL queries

**Interactions**

- powers the dashboard homepage in the frontend

### 7.14 Namespace Management Module

**Purpose**

Manages dataset storage partitions and dataset policy.

**Inputs**

- dataset create and update requests

**Outputs**

- persisted `Namespace` records exposed as datasets

**Workflow**

1. validate workspace ownership.
2. validate dataset name and domain.
3. enforce per-tenant uniqueness.
4. persist policy fields.

**Internal Logic**

- stores domain, sensitivity, freshness, minimum tier, and fallback permissions

**Interactions**

- feeds upload permissions, query routing, and retrieval behavior

### 7.15 Analytics Module

**Purpose**

Provides product and execution visibility over runs and ingestion activity.

**Inputs**

- persisted traces
- dashboard aggregates

**Outputs**

- run history
- confidence and verification signals
- operational counts

**Workflow**

1. persist run trace data at query completion.
2. project traces into user-friendly run responses.
3. expose them through dashboard and runs APIs.

**Internal Logic**

- derives display-friendly run status, support summary, and provider metadata from traces

**Interactions**

- feeds dashboard and run inspector UI

### 7.16 Monitoring Module

**Purpose**

Tracks health, readiness, execution telemetry, and ingestion status.

**Inputs**

- infrastructure health probes
- request context
- persisted stage latency data

**Outputs**

- liveness and readiness responses
- structured logs
- trace and job monitoring surfaces

**Workflow**

1. perform liveness probe.
2. verify database and storage readiness.
3. bind request IDs and tenant context.
4. persist query-stage timing.

**Interactions**

- supports operators, developers, and evaluation activities

## 8. Database Structure

### 8.1 Core Entities

The database entities are:

- `tenants`
- `api_keys`
- `workspaces`
- `namespaces`
- `documents`
- `document_chunks`
- `ingestion_jobs`
- `agents`
- `agent_datasets`
- `conversations`
- `messages`
- `query_traces`

### 8.2 Tables, Fields, and Constraints

#### `tenants`

Fields:

- `tenant_id` UUID primary key
- `name` unique string
- `subscription_plan` enum
- `max_execution_tier` enum
- `default_policy` JSONB
- `retention_days` integer with positive check
- `created_at` timestamp

Purpose:

- top-level organization boundary for all resources

Constraints:

- unique tenant name
- `retention_days >= 1`

#### `api_keys`

Fields:

- `key_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `key_hash` unique string
- `label` string
- `last_used_at` timestamp nullable
- `revoked_at` timestamp nullable
- `created_at` timestamp

Purpose:

- programmatic authentication credential bound to a tenant

#### `workspaces`

Fields:

- `workspace_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `name` string
- `slug` string
- `description` text nullable
- `created_at` timestamp
- `updated_at` timestamp

Constraints:

- non-empty `name`
- non-empty `slug`
- unique `(tenant_id, name)`
- unique `(tenant_id, slug)`
- unique `(tenant_id, workspace_id)`

Purpose:

- project area grouping datasets, agents, and conversations

#### `namespaces`

Fields:

- `namespace_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `workspace_id` UUID with composite FK to `workspaces`
- `name` string
- `domain` string
- `sensitivity_level` enum
- `freshness_profile` enum
- `min_execution_tier` enum
- `allow_web_fallback` boolean
- `allow_internal_model_retrieval` boolean
- `created_at` timestamp

Constraints:

- non-empty `domain`
- unique `(tenant_id, name)`
- unique `(tenant_id, namespace_id)`

Purpose:

- dataset storage model and policy container

#### `documents`

Fields:

- `doc_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `namespace_id` composite FK to `namespaces`
- `object_key` text
- `source_uri` text nullable
- `mime_type` string
- `title` string nullable
- `checksum` string
- `file_size_bytes` bigint
- `published_at` timestamp nullable
- `version` string nullable
- `status` enum
- `created_at` timestamp

Constraints:

- unique `(tenant_id, namespace_id, checksum)`
- unique `(tenant_id, doc_id)`
- `file_size_bytes >= 0`

Purpose:

- canonical stored source file and document metadata record

#### `document_chunks`

Fields:

- `chunk_row_id` UUID primary key
- `chunk_id` string
- `tenant_id` foreign key to `tenants`
- `namespace_id` composite FK to `namespaces`
- `doc_id` composite FK to `documents`
- `chunk_index` integer
- `chunk_text` text
- `section_title` string nullable
- `section_slug` string nullable
- `chunk_role` string
- `starts_with_heading` boolean
- `is_list_block` boolean
- `search_vector` computed tsvector
- `token_count` integer
- `character_count` integer
- `start_token` integer
- `end_token` integer
- `created_at` timestamp

Constraints:

- unique `(tenant_id, chunk_id)`
- unique `(tenant_id, doc_id, chunk_index)`
- non-negative token and character counts
- `end_token >= start_token`

Purpose:

- sparse-searchable chunk store in PostgreSQL

#### `ingestion_jobs`

Fields:

- `job_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `doc_id` composite FK to `documents`
- `status` enum
- `attempt_count` integer
- `error_code` string nullable
- `error_detail` text nullable
- `started_at` timestamp nullable
- `completed_at` timestamp nullable
- `created_at` timestamp

Constraints:

- `attempt_count >= 0`

Purpose:

- execution record for document ingestion lifecycle

#### `agents`

Fields:

- `agent_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `workspace_id` composite FK to `workspaces`
- `name` string
- `description` text nullable
- `system_instructions` text
- `default_mode` enum
- `allowed_modes` JSONB
- `status` enum
- `created_at` timestamp
- `updated_at` timestamp

Constraints:

- unique `(tenant_id, workspace_id, name)`
- unique `(tenant_id, agent_id)`

Purpose:

- reusable grounded assistant configuration

#### `agent_datasets`

Fields:

- `attachment_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `agent_id` composite FK to `agents`
- `dataset_id` composite FK to `namespaces`
- `created_at` timestamp

Constraints:

- unique `(tenant_id, agent_id, dataset_id)`

Purpose:

- many-to-many attachment between agents and datasets

#### `conversations`

Fields:

- `conversation_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `workspace_id` composite FK to `workspaces`
- `agent_id` composite FK to `agents`
- `created_by_api_key_id` FK to `api_keys` nullable
- `title` string
- `last_used_mode` enum
- `created_at` timestamp
- `updated_at` timestamp

Constraints:

- non-empty `title`
- unique `(tenant_id, conversation_id)`

Purpose:

- chat thread under an agent

#### `messages`

Fields:

- `message_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `conversation_id` composite FK to `conversations`
- `created_by_api_key_id` FK to `api_keys` nullable
- `run_id` UUID nullable
- `role` enum
- `content` text
- `created_at` timestamp

Constraints:

- non-empty `content`
- unique `(tenant_id, message_id)`

Purpose:

- immutable persisted conversation history

#### `query_traces`

Fields:

- `trace_id` UUID primary key
- `tenant_id` foreign key to `tenants`
- `namespace_id` composite FK to `namespaces` nullable
- `agent_id` composite FK to `agents` nullable
- `conversation_id` composite FK to `conversations` nullable
- `selected_mode` enum nullable
- `requested_tier` enum nullable
- `router_recommendation` enum
- `effective_tier` enum
- `routing_reason` text
- `query_redacted` text
- `query_ciphertext` binary nullable
- `retrieved_chunk_ids` JSONB
- `selected_evidence_ids` JSONB
- `generator_provider` string
- `verifier_result` JSONB
- `final_answer_redacted` text
- `citations` JSONB
- `overall_confidence` float
- `degraded_reasons` JSONB
- `stage_latencies_ms` JSONB
- `total_latency_ms` integer
- `token_usage` JSONB
- `created_at` timestamp

Constraints:

- `0 <= overall_confidence <= 1`
- `total_latency_ms >= 0`

Purpose:

- authoritative run and audit record for grounded execution

### 8.3 Relationships

- one tenant has many API keys, workspaces, datasets, documents, jobs, agents, conversations, messages, and query traces
- one workspace belongs to one tenant and has many datasets, agents, and conversations
- one dataset belongs to one tenant and one workspace and has many documents and traces
- one document belongs to one dataset and has many ingestion jobs and chunk rows
- one agent belongs to one workspace and is linked to many datasets through `agent_datasets`
- one conversation belongs to one agent and contains many messages
- one query trace may belong to one dataset, one agent, and one conversation

### 8.4 ER Explanation

The ER structure is intentionally tenant-centric. All product objects are anchored by `tenant_id`, which provides the primary isolation boundary. `Workspace` organizes activity, `Namespace` expresses dataset policy, `Document` and `DocumentChunkRecord` provide the retrieval substrate, and `QueryTrace` captures runtime provenance. `Agent`, `Conversation`, and `Message` form the product chat shell layered over the dataset-backed RAG core.

## 9. APIs

### 9.1 Health APIs

#### `GET /health/live`

- Purpose: report application liveness
- Request body: none
- Response body: `{ status }`
- Workflow: returns `alive` when the process is running
- Files involved: `backend/app/api/v1/health.py`, `backend/app/schemas/health.py`

#### `GET /health/ready`

- Purpose: report readiness of configuration, database, and storage
- Request body: none
- Response body: `{ status, service, environment, version, checks }`
- Workflow: validates database connectivity and storage readiness, then returns 200 or 503
- Files involved: `backend/app/api/v1/health.py`, `backend/app/core/database.py`, `backend/app/core/storage.py`

### 9.2 Authentication APIs

#### `POST /v1/auth/email/sign-up`

- Purpose: create a preview account and initial workspace access
- Request body: email, password, optional profile and organization/workspace information
- Response body: authenticated tenant, workspace, plan, tier, API key, and creation flags
- Workflow: creates or resolves tenant and workspace context, issues API key, returns usable session payload
- Files involved: `backend/app/api/v1/auth.py`, `backend/app/services/auth.py`, `backend/app/schemas/auth.py`

#### `POST /v1/auth/email/sign-in`

- Purpose: sign in using email and password
- Request body: email and password
- Response body: authenticated tenant, workspace, plan, tier, and API key
- Workflow: validates credentials and returns an API-key-backed authenticated session
- Files involved: `backend/app/api/v1/auth.py`, `backend/app/services/auth.py`, `backend/app/schemas/auth.py`

#### `GET /v1/auth/smoke`

- Purpose: verify authenticated tenant resolution
- Request body: none
- Response body: authenticated tenant and API key metadata
- Workflow: reads the current `TenantContext` and returns it
- Files involved: `backend/app/api/v1/auth.py`, `backend/app/api/deps.py`

### 9.3 Workspace APIs

#### `POST /v1/workspaces`

- Purpose: create a workspace
- Request body: name, slug, optional description
- Response body: workspace object
- Workflow: validates tenant ownership and uniqueness, then persists workspace
- Files involved: `backend/app/api/v1/workspaces.py`, `backend/app/services/workspaces.py`, `backend/app/schemas/workspaces.py`

#### `GET /v1/workspaces`

- Purpose: list tenant workspaces
- Request body: none
- Response body: list of workspace objects
- Workflow: returns all workspaces owned by the authenticated tenant
- Files involved: `backend/app/api/v1/workspaces.py`, `backend/app/services/workspaces.py`

#### `GET /v1/workspaces/{workspace_id}`

- Purpose: fetch one workspace
- Request body: none
- Response body: workspace object
- Workflow: verifies tenant ownership and returns the workspace
- Files involved: `backend/app/api/v1/workspaces.py`, `backend/app/services/workspaces.py`

#### `PATCH /v1/workspaces/{workspace_id}`

- Purpose: update a workspace
- Request body: patchable workspace fields
- Response body: updated workspace object
- Workflow: validates tenant ownership, applies changes, and persists them
- Files involved: `backend/app/api/v1/workspaces.py`, `backend/app/services/workspaces.py`

### 9.4 Dataset APIs

#### `POST /v1/datasets`

- Purpose: create a dataset
- Request body: workspace ID, name, domain, sensitivity, freshness, minimum tier, fallback flags
- Response body: dataset object
- Workflow: validates workspace ownership, ensures dataset uniqueness, persists namespace-backed dataset
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`, `backend/app/schemas/datasets.py`

#### `GET /v1/datasets`

- Purpose: list datasets, optionally by workspace
- Request body: none
- Query params: `workspace_id` optional
- Response body: list of dataset objects
- Workflow: validates workspace if supplied and returns tenant-scoped datasets
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`

#### `GET /v1/datasets/{dataset_id}`

- Purpose: fetch one dataset
- Request body: none
- Response body: dataset object
- Workflow: resolves the dataset for the current tenant
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`

#### `PATCH /v1/datasets/{dataset_id}`

- Purpose: update dataset policy or metadata
- Request body: patchable dataset fields
- Response body: updated dataset object
- Workflow: validates ownership and applies allowed dataset changes
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`

#### `GET /v1/datasets/{dataset_id}/documents`

- Purpose: list documents within a dataset
- Request body: none
- Response body: list of dataset document objects
- Workflow: verifies dataset ownership and returns tenant-scoped documents
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`

#### `GET /v1/datasets/{dataset_id}/ingestion-jobs`

- Purpose: list ingestion jobs within a dataset
- Request body: none
- Response body: list of ingestion job objects
- Workflow: resolves tenant-scoped jobs and maps them to dataset-specific responses
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/datasets.py`

#### `POST /v1/datasets/{dataset_id}/upload`

- Purpose: upload a document into a dataset and start ingestion
- Request body: multipart form with file and optional title
- Response body: dataset upload response containing document and job IDs
- Workflow: stores the file, creates document and ingestion job records, and schedules ingestion when enabled
- Files involved: `backend/app/api/v1/datasets.py`, `backend/app/services/documents.py`, `backend/app/workers/pipeline.py`

### 9.5 Document APIs

#### `POST /v1/documents/upload`

- Purpose: direct document upload to a namespace
- Request body: multipart form with `namespace_id`, file, and optional title
- Response body: upload response
- Workflow: identical to dataset upload, but namespace-targeted
- Files involved: `backend/app/api/v1/documents.py`, `backend/app/services/documents.py`

#### `GET /v1/ingestion-jobs/{job_id}`

- Purpose: retrieve ingestion job status
- Request body: none
- Response body: ingestion job status object
- Workflow: verifies tenant ownership and returns current job lifecycle state
- Files involved: `backend/app/api/v1/documents.py`, `backend/app/services/documents.py`

#### `POST /v1/documents/{document_id}/reindex`

- Purpose: queue a document for reindexing
- Request body: none
- Response body: reindex response containing new job details
- Workflow: resolves the document, creates a fresh ingestion job, and schedules background processing
- Files involved: `backend/app/api/v1/documents.py`, `backend/app/services/documents.py`

### 9.6 Agent APIs

#### `POST /v1/agents`

- Purpose: create an agent
- Request body: workspace ID, name, description, system instructions, default mode, allowed modes
- Response body: agent object
- Workflow: validates workspace ownership and persists the agent configuration
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`, `backend/app/schemas/agents.py`

#### `GET /v1/agents`

- Purpose: list agents
- Request body: none
- Query params: `workspace_id` optional
- Response body: list of agent objects
- Workflow: returns tenant-scoped agents and their dataset attachments
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`

#### `GET /v1/agents/{agent_id}`

- Purpose: get one agent
- Request body: none
- Response body: agent object
- Workflow: validates tenant ownership and returns the agent with dataset links
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`

#### `PATCH /v1/agents/{agent_id}`

- Purpose: update agent configuration
- Request body: patchable agent fields
- Response body: updated agent object
- Workflow: validates ownership and persists changes
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`

#### `POST /v1/agents/{agent_id}/datasets`

- Purpose: attach a dataset to an agent
- Request body: dataset ID
- Response body: updated agent object
- Workflow: validates same-tenant, same-workspace compatibility and creates the attachment
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`

#### `DELETE /v1/agents/{agent_id}/datasets/{dataset_id}`

- Purpose: detach a dataset from an agent
- Request body: none
- Response body: no content
- Workflow: removes the agent-dataset link after tenant validation
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agents.py`

#### `POST /v1/agents/{agent_id}/chat`

- Purpose: execute one agent chat turn
- Request body: conversation ID, message, optional mode, optional dataset ID
- Response body: chat response with answer, citations, trust signals, and message IDs
- Workflow: validates agent and conversation, resolves mode and dataset, creates user message, executes grounded query, creates assistant message, updates conversation mode, returns run-linked response
- Files involved: `backend/app/api/v1/agents.py`, `backend/app/services/agent_chat.py`, `backend/app/services/query.py`, `backend/app/services/messages.py`

### 9.7 Conversation APIs

#### `POST /v1/agents/{agent_id}/conversations`

- Purpose: create a conversation under an agent
- Request body: conversation creation fields such as title
- Response body: conversation object
- Workflow: validates agent ownership and persists a new conversation
- Files involved: `backend/app/api/v1/conversations.py`, `backend/app/services/conversations.py`

#### `GET /v1/agents/{agent_id}/conversations`

- Purpose: list conversations for an agent
- Request body: none
- Response body: list of conversation objects
- Workflow: returns tenant-scoped conversations for the selected agent
- Files involved: `backend/app/api/v1/conversations.py`, `backend/app/services/conversations.py`

#### `GET /v1/conversations/{conversation_id}`

- Purpose: get one conversation
- Request body: none
- Response body: conversation object
- Workflow: validates tenant ownership and returns the conversation
- Files involved: `backend/app/api/v1/conversations.py`, `backend/app/services/conversations.py`

#### `PATCH /v1/conversations/{conversation_id}`

- Purpose: update conversation metadata
- Request body: patchable conversation fields
- Response body: updated conversation object
- Workflow: applies conversation updates such as title changes
- Files involved: `backend/app/api/v1/conversations.py`, `backend/app/services/conversations.py`

#### `GET /v1/conversations/{conversation_id}/messages`

- Purpose: list conversation messages
- Request body: none
- Response body: list of message objects
- Workflow: validates ownership and returns immutable message history
- Files involved: `backend/app/api/v1/conversations.py`, `backend/app/services/messages.py`

### 9.8 Query API

#### `POST /v1/query`

- Purpose: run a grounded query directly against a dataset
- Request body: dataset ID, query text, optional requested tier
- Response body: grounded answer response
- Workflow: performs tenant validation, query analysis, routing, hybrid retrieval, evidence packaging, grounded generation, response shaping, verification, and trace persistence
- Files involved: `backend/app/api/v1/query.py`, `backend/app/services/query.py`, `backend/app/services/retrieval.py`, `backend/app/services/evidence.py`, `backend/app/services/generation.py`, `backend/app/services/response_shaping.py`, `backend/app/services/verification.py`

### 9.9 Run APIs

#### `GET /v1/runs`

- Purpose: list recent runs
- Request body: none
- Query params: `dataset_id` optional, `limit`
- Response body: list of run objects
- Workflow: projects `QueryTrace` records into product-facing run responses
- Files involved: `backend/app/api/v1/runs.py`, `backend/app/services/runs.py`

#### `GET /v1/runs/{run_id}`

- Purpose: get one run in detail
- Request body: none
- Response body: run object with citations and trace-derived fields
- Workflow: validates tenant ownership and returns projected run data
- Files involved: `backend/app/api/v1/runs.py`, `backend/app/services/runs.py`

### 9.10 Dashboard APIs

#### `GET /v1/dashboard/summary`

- Purpose: return top-level dashboard counts
- Request body: none
- Response body: summary counts for datasets, documents, jobs, agents, and conversations
- Workflow: executes tenant-scoped aggregate counts
- Files involved: `backend/app/api/v1/dashboard.py`, `backend/app/services/dashboard.py`

#### `GET /v1/dashboard/recent-runs`

- Purpose: return recent run activity
- Request body: none
- Query params: `limit`
- Response body: list of run objects
- Workflow: delegates to run listing for dashboard activity
- Files involved: `backend/app/api/v1/dashboard.py`, `backend/app/services/dashboard.py`, `backend/app/services/runs.py`

#### `GET /v1/dashboard/recent-jobs`

- Purpose: return recent ingestion job activity
- Request body: none
- Query params: `limit`
- Response body: list of recent job objects with dataset and document context
- Workflow: joins ingestion jobs to documents and returns dashboard-ready activity rows
- Files involved: `backend/app/api/v1/dashboard.py`, `backend/app/services/dashboard.py`

### 9.11 API Key APIs

#### `GET /v1/api-keys`

- Purpose: list tenant API keys
- Request body: none
- Response body: list of safe API key metadata
- Workflow: returns hashed-key metadata without exposing raw secrets
- Files involved: `backend/app/api/v1/api_keys.py`, `backend/app/services/api_keys.py`

#### `POST /v1/api-keys`

- Purpose: create an API key
- Request body: key label
- Response body: API key metadata plus raw API key shown once
- Workflow: generates new credential material, stores hash, and returns the raw secret once
- Files involved: `backend/app/api/v1/api_keys.py`, `backend/app/services/api_keys.py`

#### `POST /v1/api-keys/{key_id}/revoke`

- Purpose: revoke an API key
- Request body: none
- Response body: revoked API key metadata
- Workflow: marks the key as revoked and prevents future authentication
- Files involved: `backend/app/api/v1/api_keys.py`, `backend/app/services/api_keys.py`

### 9.12 Capabilities API

#### `GET /v1/capabilities`

- Purpose: return current product and mode availability
- Request body: none
- Response body: capabilities object containing modes and entitlements
- Workflow: derives visible product capabilities from tenant plan and backend configuration
- Files involved: `backend/app/api/v1/capabilities.py`, `backend/app/services/capabilities.py`, `backend/app/schemas/capabilities.py`

## 10. UI Components

The final UI includes the following major product components:

### 10.1 Landing Experience

- marketing navigation
- product promise and architecture-oriented messaging
- capabilities and trust sections
- mode and enterprise positioning

### 10.2 Authentication Interfaces

- email sign-in
- email sign-up
- API key developer access
- theme toggle and product identity elements

### 10.3 Onboarding Wizard

- personal information step
- organization and workspace step
- industry and use-case step
- workspace creation confirmation step

### 10.4 Workspace Dashboard

- quick actions for dataset, agent, and upload flows
- summary cards
- recent runs panel
- recent ingestion jobs panel
- mode and live-tier status card

### 10.5 Dataset Management UI

- dataset list with search
- dataset creation form
- dataset detail view
- drag-and-drop upload area
- document listing
- ingestion job listing
- dataset policy and readiness side panels

### 10.6 Agent Management UI

- agent list with search
- agent creation form
- mode selection controls
- dataset attachment workflow
- agent detail and chat shell

### 10.7 Agent Chat UI

- conversation list
- dataset selector for multi-dataset agents
- mode selector
- optimistic user and assistant state handling
- typing/generation indicators
- run-linked answer inspection
- citation, confidence, and degraded-status display

### 10.8 Run Inspector UI

- recent run list
- run detail panel
- answer view
- routing reason
- confidence display
- citation cards
- degraded reason explanations

### 10.9 Settings and Developer Access UI

- plan and capability summary
- API key creation and copy-once flow
- API key revocation
- enterprise and governance-oriented settings placeholders within the full product shell

## 11. Technology Stack

### Frontend

- React
- TypeScript
- React Router
- TanStack Query
- Tailwind CSS
- Framer Motion
- Sonner
- Lucide icons

### Backend

- Python
- FastAPI
- SQLAlchemy Async
- Pydantic schemas

### Storage and Data

- PostgreSQL
- Qdrant
- MinIO / S3-compatible object storage
- Redis in platform stack support

### Document Processing

- `pypdf` for PDF extraction
- `python-docx` for DOCX extraction

### Deployment and Operations

- Docker
- Docker Compose
- Alembic migrations
- GitHub Actions CI

### Model and Retrieval Integrations

- local grounded generator
- Gemini generation integration
- OpenAI-compatible generation integration
- embedding backends configured through core adapters

## 12. Security

The system incorporates multiple security controls:

- API key authentication with hashed storage
- optional Bearer-formatted API key support for interoperability
- strict tenant-scoped database access patterns
- workspace and dataset ownership validation in service methods
- dataset policy controls for minimum execution tier, web fallback, and internal model retrieval
- redacted trace persistence for safer audit records
- revocable API keys with usage timestamps
- readiness and configuration checks at startup and runtime
- CORS origin allowlisting

The architecture also enforces a critical design principle: data is always tenant-owned and dataset-scoped, regardless of the execution tier used to process a query.

## 13. Deployment

The deployment model consists of:

- frontend client application
- backend API service
- PostgreSQL database
- Qdrant vector service
- object storage service
- Redis support service

Local and self-hosted environments are orchestrated through Docker Compose. The backend container exposes the FastAPI service, while PostgreSQL stores product and retrieval state, Qdrant stores vector points, and MinIO stores source files and ingestion artifacts.

Readiness is determined by:

- valid application configuration
- successful database connectivity
- successful object storage access

This design supports both development and production-shaped deployments with clear dependency boundaries.

## 14. Evaluation Approach

The system is evaluated as a grounded document-intelligence platform rather than a generic chatbot. The evaluation approach focuses on:

- retrieval quality over tenant-scoped datasets
- grounding quality of answers against cited evidence
- correctness of citation mapping
- degraded honesty when support is weak
- execution-tier routing quality
- latency by pipeline stage
- ingestion reliability across supported file formats
- run trace completeness for audit and analysis

The backend also includes evaluation-oriented infrastructure such as:

- persisted `QueryTrace` records with stage latencies and evidence metadata
- run history endpoints for manual and scripted inspection
- pilot evaluation scripts under `backend/scripts`
- automated tests across config, database, auth, telemetry, models, and query behaviors

For a final-year project context, the evaluation should be reported across both functional and quality dimensions:

- functional correctness of uploads, indexing, querying, and chat
- trustworthiness measured through citations and degraded behavior
- usability of the dashboard workflows
- architectural soundness of multitenancy, tier routing, and traceability

## 15. Important Notes

### 15.1 Canonical Product Identity

The final system title is best represented as **Grounded AI**, implemented in this repository as the **grounding-engine** backend and frontend platform.

### 15.2 Core Architectural Principle

The most important architectural principle in the project is the separation of:

- subscription plans
- user-facing modes
- execution tiers
- dataset policy
- runtime routing

This separation is what makes the system explainable, governable, and adaptable.

### 15.3 Dataset Policy Significance

Datasets are not only storage buckets. They also encode governance and routing rules through:

- domain
- sensitivity
- freshness profile
- minimum execution tier
- web fallback permission
- internal model retrieval permission

These fields are fundamental to how the final platform governs grounded behavior.

### 15.4 Trust Model

The system trust model depends on five layers working together:

- tenant and dataset isolation
- hybrid retrieval
- compact evidence packaging
- strict citation validation
- degraded honesty and verification

This means the platform is intentionally designed to abstain or degrade when evidence is insufficient instead of fabricating certainty.

### 15.5 Run Trace Importance

`QueryTrace` is one of the most important records in the entire system because it preserves:

- what the user asked
- how the system routed the request
- which evidence was retrieved
- which evidence was selected
- what answer was returned
- why confidence and degraded decisions were assigned

This makes the platform suitable for evaluation, audit, trust analysis, and product transparency.

### 15.6 Product-Shell Completeness

The final system is not just a backend RAG API. It is a complete product shell with:

- account access
- onboarding
- workspace creation
- dataset lifecycle management
- document ingestion visibility
- grounded agent creation
- conversation history
- run inspection
- developer API key administration

### 15.7 Supported Document Types

The ingestion pipeline natively supports:

- TXT
- PDF
- DOCX

These formats cover common enterprise and academic knowledge workflows.

### 15.8 Retrieval Design Choice

The retrieval design intentionally uses:

- PostgreSQL full-text search for sparse retrieval
- Qdrant for dense semantic retrieval

This hybrid design provides a practical and effective balance between exact term matching and semantic relevance.

### 15.9 User Experience Philosophy

The product communicates depth through intuitive modes such as `Instant`, `Thinking`, and `Verified` instead of exposing low-level routing vocabulary as the primary UI metaphor. This improves usability without weakening the backend architecture.

### 15.10 Final System Characterization

Grounded AI is best characterized as a multitenant grounded intelligence platform that combines managed ingestion, hybrid retrieval, tiered query processing, reusable agents, structured citations, trust calibration, and auditable run tracing into one coherent enterprise-ready document intelligence system.
