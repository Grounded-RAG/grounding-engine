# Standard Tier And Phase 1

## Purpose

This document explains the **current implemented Standard tier** in Grounded and
what **Phase 1** delivered.

It is intentionally concrete. It describes the system that exists in the
backend today, not the future Enterprise or Critical roadmap.

If you want the broader product model, read:

- `docs/SOLUTION_ARCHITECTURE.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/IMPLEMENTATION_PLAN.md`

---

## 1. What Standard Tier Means

Standard is Grounded's first fully usable runtime tier.

It is the baseline production RAG path for tenant-scoped document Q&A. The goal
of Standard is to be:

- grounded
- tenant-safe
- traceable
- honest when evidence is weak
- fast enough for normal use

Standard is **not** the heavy agentic path. It does not try to run planners,
rerankers, external search, or critic loops on every query.

Instead, Standard gives us a strong baseline with:

- authenticated tenant and namespace scoping
- automatic ingestion after upload
- deterministic chunking
- hybrid sparse + dense retrieval
- Reciprocal Rank Fusion (RRF)
- evidence packaging
- grounded answer generation
- structured citations
- degraded responses when evidence is insufficient
- persisted query traces

---

## 2. What Phase 1 Implemented

Phase 1 implemented the complete Standard-tier flow:

1. document upload
2. ingestion job creation
3. automatic ingestion pipeline execution
4. extraction and metadata enrichment
5. deterministic chunking
6. dense indexing
7. sparse indexing
8. hybrid retrieval with RRF
9. evidence packaging
10. grounded generation
11. structured citation responses
12. degraded answer handling
13. query trace persistence
14. Standard query endpoint

In practical product terms, that means a tenant can now:

1. upload a supported file
2. wait for the ingestion job to become `indexed`
3. query that namespace
4. receive a grounded answer with citations

---

## 3. What Standard Does Not Include

These are intentionally **not** part of Phase 1 Standard:

- query planner or decomposition by default
- semantic chunking as the default chunker
- temporal scoring
- reranking
- Corrective RAG or web fallback
- internal model retrieval
- critic / verification loop

Those are reserved for later tiers:

- Enterprise adds retrieval-precision upgrades
- Critical adds highest-assurance verification behavior

---

## 4. Standard Tier End-To-End Flow

### High-level flow

```text
Client
  -> POST /v1/documents/upload
  -> document row created
  -> ingestion job created
  -> background Standard ingestion pipeline runs
      -> extraction
      -> metadata enrichment
      -> deterministic chunking
      -> dense indexing
      -> sparse indexing
  -> ingestion job becomes indexed
  -> POST /v1/query
      -> sparse retrieval
      -> dense retrieval
      -> RRF fusion
      -> evidence packaging
      -> grounded generation
      -> structured response shaping
      -> trace persistence
  -> grounded answer + citations
```

### Runtime characteristic

The current Phase 1 implementation uses **FastAPI background tasks** for
automatic ingestion. That means:

- upload returns quickly after the file and DB records are persisted
- ingestion continues asynchronously in the application process
- clients should poll the ingestion job endpoint until the job is `indexed`

This is accurate for the current implementation. A separate queue worker can be
introduced later, but it is not required for the Phase 1 Standard slice.

---

## 5. Authentication And Tenant Scoping

All protected Standard endpoints use API-key-based tenant resolution.

Supported auth inputs:

- `X-API-Key` header
- `Authorization: Bearer <api-key>`

The backend resolves a `TenantContext` that includes:

- `tenant_id`
- `tenant_name`
- `subscription_plan`
- `max_execution_tier`
- `api_key_id`
- `api_key_label`

Every upload, ingestion lookup, and query is tenant-scoped. A tenant cannot
access another tenant's namespace, document, ingestion job, or query path.

Core routing rule for Phase 1 Standard:

- data belongs to `tenant + namespace`
- queries run only in the `standard` execution tier

If a namespace requires a higher minimum tier, the Standard query endpoint
returns a conflict instead of silently downgrading the safety level.

---

## 6. Ingestion Inputs And Outputs

### 6.1 Upload endpoint

Endpoint:

- `POST /v1/documents/upload`

Request type:

- `multipart/form-data`

Required inputs:

- `namespace_id` as a form field
- `file` as the uploaded file

Optional input:

- `title`

Supported file types:

- `.txt` -> `text/plain`
- `.pdf` -> `application/pdf`
- `.docx` -> `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

Current default size limit:

- `25 MB`

Validation behavior:

- file must have a filename
- extension must be one of the supported types
- content type must match the extension unless the upload uses a generic binary
  content type
- file must not be empty
- file size must be below `DOCUMENT_UPLOAD_MAX_BYTES`
- namespace must belong to the authenticated tenant

Successful response shape:

```json
{
  "document_id": "uuid",
  "namespace_id": "uuid",
  "job_id": "uuid",
  "filename": "policy.pdf",
  "title": "Policy",
  "mime_type": "application/pdf",
  "file_size_bytes": 12345,
  "document_status": "uploaded",
  "job_status": "queued"
}
```

### 6.2 Ingestion job status endpoint

Endpoint:

- `GET /v1/ingestion-jobs/{job_id}`

Successful response shape:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "indexed",
  "attempt_count": 1,
  "error_code": null,
  "error_detail": null,
  "started_at": "2026-03-22T12:00:00Z",
  "completed_at": "2026-03-22T12:00:01Z",
  "created_at": "2026-03-22T11:59:59Z"
}
```

### 6.3 Lifecycle states

Document lifecycle states used by Standard:

- `uploaded`
- `processing`
- `indexed`
- `failed`

Ingestion job lifecycle states defined in the model:

- `queued`
- `running`
- `indexed`
- `failed`
- `dead_letter`

Current Standard autorun path normally uses:

- `queued -> running -> indexed`

or:

- `queued -> running -> failed`

`dead_letter` exists in the enum/model contract, but it is not part of the
current Phase 1 Standard happy path.

---

## 7. What Happens During Ingestion

### Step 1. Raw file storage

After validation, the source file is written to object storage with a
tenant-scoped key:

```text
tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/source/{filename}
```

The backend also creates:

- one `documents` row
- one `ingestion_jobs` row

### Step 2. Automatic Standard pipeline kickoff

If `INGESTION_AUTORUN_ENABLED=true`, the upload route schedules the Standard
pipeline in the background.

### Step 3. Extraction

The extraction step:

- downloads the raw source object
- extracts text for TXT, PDF, or DOCX
- normalizes line endings and text format
- rejects empty extraction output
- writes normalized extracted text back to object storage

Extracted text artifact key:

```text
tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/artifacts/extracted/text.txt
```

### Step 4. Metadata enrichment

During extraction, the backend may improve document metadata using file content:

- title
- publication / creation timestamp when available

Examples:

- PDF metadata may provide `/Title` and `/CreationDate`
- DOCX core properties may provide title and created timestamp

### Step 5. Deterministic chunking

The chunking step:

- loads the normalized extracted text artifact
- splits it into deterministic overlapping token windows
- preserves stable chunk order
- assigns stable chunk ids and offsets
- persists a chunk manifest artifact

Current default chunking config:

- `CHUNK_MAX_TOKENS = 256`
- `CHUNK_OVERLAP_TOKENS = 40`

Chunk manifest key:

```text
tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/artifacts/chunks/manifest.json
```

### Step 6. Dense indexing

The dense indexing step:

- reads the chunk manifest
- builds deterministic dense embeddings
- ensures the configured Qdrant collection exists
- upserts one vector point per chunk

Current defaults:

- `QDRANT_COLLECTION = grounded_chunks`
- `DENSE_EMBEDDING_DIMENSIONS = 128`

Each dense point includes payload metadata for:

- tenant
- namespace
- document
- chunk
- chunk text

### Step 7. Sparse indexing

The sparse indexing step:

- materializes chunk rows into PostgreSQL
- stores chunk text and ordering metadata
- populates the full-text search vector used by Standard lexical retrieval

This gives Standard its keyword / exact-match retrieval path.

### Step 8. Final indexed state

After dense and sparse indexing succeed:

- document status becomes `indexed`
- ingestion job status becomes `indexed`

At that point the document is ready to query.

---

## 8. Where Standard Stores Data

Standard currently stores data across three places:

### Object storage

Used for:

- raw uploaded files
- normalized extracted text artifacts
- chunk manifest artifacts

### PostgreSQL

Used for:

- tenants
- namespaces
- api keys
- documents
- ingestion jobs
- sparse chunk rows
- query traces

### Qdrant

Used for:

- dense vector representations of document chunks

This separation is intentional:

- object storage holds large durable file artifacts
- PostgreSQL holds relational state and full-text search data
- Qdrant holds semantic vector search data

---

## 9. Query Inputs And Outputs

### 9.1 Query endpoint

Endpoint:

- `POST /v1/query`

Request body:

```json
{
  "namespace_id": "uuid",
  "query": "What is the maintenance window?"
}
```

Response body:

```json
{
  "answer": "Maintenance window: Friday at 22:00 UTC. [E001]",
  "citations": [
    {
      "citation_id": "E001",
      "chunk_id": "chunk-id",
      "document_id": "uuid",
      "chunk_index": 0,
      "quote": "Maintenance window: Friday at 22:00 UTC."
    }
  ],
  "confidence_score": 0.87,
  "verification_status": "passed",
  "degraded_reasons": []
}
```

Response header:

- `X-Trace-Id: <uuid>`

The trace header is important because it links the API response to the persisted
query trace row.

### 9.2 Query response contract

The Standard query response always follows one structured contract:

- `answer`
- `citations`
- `confidence_score`
- `verification_status`
- `degraded_reasons`

`verification_status` can currently be:

- `passed`
- `degraded`

---

## 10. What Happens During Query Execution

### Step 1. Namespace validation

The query service:

- confirms the namespace belongs to the authenticated tenant
- confirms the namespace minimum tier is `standard`

If the namespace requires a higher tier, Standard does not run and returns a
conflict.

### Step 2. Sparse retrieval

The sparse path queries PostgreSQL full-text search over `document_chunks` using
`plainto_tsquery('english', ...)`.

This path is good at:

- exact terms
- names
- rare vocabulary
- policy phrases
- code-like tokens

### Step 3. Dense retrieval

The dense path:

- embeds the query text
- searches Qdrant with tenant and namespace filters
- returns semantic matches

This path is good at:

- semantic similarity
- paraphrases
- synonyms
- natural-language matches

### Step 4. Hybrid fusion with RRF

Standard merges sparse and dense candidates using Reciprocal Rank Fusion.

Current defaults:

- `RETRIEVAL_CANDIDATE_LIMIT = 8`
- `RRF_SMOOTHING_CONSTANT = 60`

The result is a fused ranked set of candidates that rewards agreement between
the sparse and dense paths.

### Step 5. Evidence packaging

The fused hits are normalized into an evidence package.

Current default:

- `EVIDENCE_PACKAGE_LIMIT = 3`

Each evidence item includes:

- stable citation id such as `E001`
- chunk id
- document id
- chunk index
- verbatim text
- fused score
- source path information (`sparse`, `dense`, or both)

### Step 6. Grounded generation

The current Standard generator:

- receives the query and packaged evidence
- composes an answer only from selected evidence
- references evidence using citation markers like `[E001]`

The current implementation is intentionally deterministic and grounded. It is
not yet the later-tier planner / critic architecture.

### Step 7. Structured response shaping

The response shaper:

- verifies that cited evidence ids are real
- creates ordered citation objects
- computes bounded confidence
- returns the typed API response

### Step 8. Degraded behavior

If there is not enough grounded evidence, Standard does **not** bluff.

Instead it returns:

- `verification_status = "degraded"`
- `confidence_score = 0.0`
- `citations = []`
- one or more `degraded_reasons`

Current degraded reasons used by Standard include:

- `NO_GROUNDED_EVIDENCE`
- `INSUFFICIENT_SUPPORT`

### Step 9. Query trace persistence

Every Standard query persists a trace row that records:

- tenant
- namespace
- requested tier
- router recommendation
- effective tier
- routing reason
- retrieved chunk ids
- selected evidence ids
- generator provider
- verification result
- final answer
- citations
- confidence
- degraded reasons
- stage latencies
- total latency

Current Phase 1 trace routing values are fixed to the Standard path:

- `requested_tier = standard`
- `router_recommendation = standard`
- `effective_tier = standard`
- `routing_reason = phase1_standard_query`

---

## 11. Standard Tier Request / Response Examples

### Example 1. Successful upload

Request:

- `POST /v1/documents/upload`
- form fields:
  - `namespace_id = <uuid>`
  - `file = handbook.txt`

Immediate response:

```json
{
  "document_id": "11111111-1111-1111-1111-111111111111",
  "namespace_id": "22222222-2222-2222-2222-222222222222",
  "job_id": "33333333-3333-3333-3333-333333333333",
  "filename": "handbook.txt",
  "title": "handbook",
  "mime_type": "text/plain",
  "file_size_bytes": 91,
  "document_status": "uploaded",
  "job_status": "queued"
}
```

Later job poll:

```json
{
  "job_id": "33333333-3333-3333-3333-333333333333",
  "document_id": "11111111-1111-1111-1111-111111111111",
  "status": "indexed",
  "attempt_count": 1,
  "error_code": null,
  "error_detail": null,
  "started_at": "2026-03-22T12:00:00Z",
  "completed_at": "2026-03-22T12:00:01Z",
  "created_at": "2026-03-22T11:59:59Z"
}
```

### Example 2. Successful Standard query

Request:

```json
{
  "namespace_id": "22222222-2222-2222-2222-222222222222",
  "query": "What is the maintenance window?"
}
```

Response:

```json
{
  "answer": "Maintenance window: Friday at 22:00 UTC. [E001]",
  "citations": [
    {
      "citation_id": "E001",
      "chunk_id": "chunk-0",
      "document_id": "11111111-1111-1111-1111-111111111111",
      "chunk_index": 0,
      "quote": "Maintenance window: Friday at 22:00 UTC."
    }
  ],
  "confidence_score": 0.87,
  "verification_status": "passed",
  "degraded_reasons": []
}
```

### Example 3. Degraded Standard query

Response:

```json
{
  "answer": "I could not find grounded evidence for this query.",
  "citations": [],
  "confidence_score": 0.0,
  "verification_status": "degraded",
  "degraded_reasons": [
    "NO_GROUNDED_EVIDENCE"
  ]
}
```

---

## 12. Browser And Swagger Testing

If the backend is running locally, Standard can be tested in the browser at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

Typical manual test flow:

1. authenticate with an API key
2. call `POST /v1/documents/upload`
3. poll `GET /v1/ingestion-jobs/{job_id}` until it becomes `indexed`
4. call `POST /v1/query`
5. inspect the JSON response and `X-Trace-Id` header

---

## 13. Why This Standard Tier Matters

Phase 1 gives Grounded a real, usable product baseline.

It proves that the system can already:

- ingest user-owned documents
- preserve tenant and namespace boundaries
- retrieve evidence with both lexical and semantic methods
- return grounded answers with citations
- avoid unsupported confident answers
- persist trace data for debugging and evaluation

This is the foundation that later tiers build on.

If Standard were weak, Enterprise and Critical would only add complexity on top
of an unstable base. Because Standard is now implemented end to end, later
tier work can focus on precision and assurance improvements instead of basic
pipeline assembly.

---

## 14. Summary

The current Grounded Standard tier is a complete baseline RAG system with:

- document upload
- automatic ingestion
- extraction
- metadata enrichment
- deterministic chunking
- dense indexing
- sparse indexing
- hybrid retrieval with RRF
- evidence packaging
- grounded generation
- structured citation responses
- degraded behavior
- query trace persistence
- Standard query API

That is the delivered scope of **Phase 1**.

---

## 15. What Comes Next

Phase 1.5 is now complete.

It added the product shell on top of the Standard runtime:

- capabilities and user-facing mode support
- workspaces
- datasets as the product-facing layer over namespaces
- agents
- conversations and messages
- run history and answer inspection
- dashboard summary and API key management
- agent chat built on top of the Standard engine

The current live mode behavior is now:

- `Auto` works on top of Standard
- `Instant` works on top of Standard
- `Thinking` stays visible but disabled
- `Verified` stays visible but disabled

The next backend phase is **Phase 2**, which turns on the Enterprise path:

- planner / query transformation
- temporal and freshness scoring
- reranking
- semantic chunking experiment behind evaluation gates
- `Thinking` mode activation once the Enterprise path proves its value

The detailed product-shell backend record remains documented in:

- `docs/PHASE_1_5_BACKEND_PLAN.md`
