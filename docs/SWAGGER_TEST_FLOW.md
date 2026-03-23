# Swagger Test Flow

This document is the reviewer-friendly manual test plan for the current
Grounded backend.

It is written for the backend that exists :

- Phase 1 Standard engine: live
- Phase 1.5 product-shell backend: live
- `Auto` and `Instant`: live
- `Thinking` and `Verified`: visible but intentionally unavailable

## 1. Before Swagger

Start the local stack:

```bash
docker compose up -d postgres redis qdrant minio
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Generate a demo API key from the repository root:

```bash
python backend/scripts/seed_demo_tenant.py
```

Open Swagger:

```text
http://localhost:8000/docs
```

Click `Authorize` and paste the API key into `X-API-Key`.

Prepare a small file for upload, for example `advisor-demo.txt`:

```text
Maintenance window: Friday at 22:00 UTC.
Escalation contact: ops@example.com.
Support window: Monday at 09:00 UTC.
```

## 2. Recommended Test Order

Test the backend in this order:

1. root and health
2. auth and capabilities
3. workspaces
4. datasets
5. upload and ingestion jobs
6. agents
7. conversations
8. agent chat
9. messages and runs
10. dashboard
11. API key management
12. optional legacy Standard endpoints

## 3. Endpoint-by-Endpoint Flow

### 3.1 Root and Health

`GET /`

Expected:

```json
{
  "service": "Grounded Backend",
  "environment": "development",
  "version": "0.1.0"
}
```

`GET /health/live`

Expected:

```json
{
  "status": "alive"
}
```

`GET /health/ready`

Expected:

```json
{
  "status": "ready",
  "checks": {
    "config": "ok",
    "database": "ok",
    "storage": "ok"
  }
}
```

### 3.2 Authentication and Capabilities

`GET /v1/auth/smoke`

Expected fields:

- `status`
- `tenant_id`
- `tenant_name`
- `subscription_plan`
- `max_execution_tier`
- `api_key_id`
- `api_key_label`

`GET /v1/capabilities`

Expected:

- `default_mode = auto`
- `manual_mode_override_allowed = true`
- `auto` enabled
- `instant` enabled
- `thinking` disabled with an availability reason
- `verified` disabled with an availability reason

### 3.3 Workspaces

`POST /v1/workspaces`

Body:

```json
{
  "name": "Advisor Demo Workspace",
  "description": "Workspace for Swagger review"
}
```

Expected:

- `201 Created`
- response contains `workspace_id`, `name`, `slug`, `description`

Save `workspace_id`.

`GET /v1/workspaces`

Expected:

- a list containing the workspace you just created

`GET /v1/workspaces/{workspace_id}`

Expected:

- the exact workspace resource

`PATCH /v1/workspaces/{workspace_id}`

Body:

```json
{
  "description": "Updated workspace description"
}
```

Expected:

- `200 OK`
- same `workspace_id`
- updated `description`

### 3.4 Datasets

`POST /v1/datasets`

Body:

```json
{
  "workspace_id": "PASTE_WORKSPACE_ID",
  "name": "Operations Dataset",
  "domain": "operations"
}
```

Expected:

- `201 Created`
- response contains `dataset_id`
- `min_execution_tier = "standard"`

Save `dataset_id`.

`GET /v1/datasets`

Expected:

- list includes the created dataset

`GET /v1/datasets/{dataset_id}`

Expected:

- exact dataset resource

`PATCH /v1/datasets/{dataset_id}`

Body:

```json
{
  "domain": "operations-updated"
}
```

Expected:

- updated dataset with the new `domain`

### 3.5 Upload and Ingestion

`POST /v1/datasets/{dataset_id}/upload`

Use `multipart/form-data`:

- `file`: `advisor-demo.txt`
- `title`: `Advisor Demo Handbook`

Expected for a new upload:

- `201 Created`
- `already_exists = false`
- `document_id`
- `job_id`
- `document_status`
- `job_status`

Save `job_id`.

If you upload the exact same bytes again into the same dataset:

- expect `200 OK`
- expect `already_exists = true`
- expect the existing document/job to be reused

`GET /v1/ingestion-jobs/{job_id}`

Poll until:

```json
{
  "status": "indexed"
}
```

`GET /v1/datasets/{dataset_id}/documents`

Expected:

- document list for the dataset
- uploaded document appears here

`GET /v1/datasets/{dataset_id}/ingestion-jobs`

Expected:

- job list for the dataset
- uploaded job appears here

### 3.6 Agents

`POST /v1/agents`

Body:

```json
{
  "workspace_id": "PASTE_WORKSPACE_ID",
  "name": "Operations Assistant",
  "description": "Grounded ops assistant",
  "default_mode": "auto",
  "allowed_modes": ["auto", "instant"]
}
```

Expected:

- `201 Created`
- `agent_id`
- `dataset_ids = []`

Save `agent_id`.

`GET /v1/agents`

Expected:

- list includes your agent

`GET /v1/agents/{agent_id}`

Expected:

- exact agent resource

`PATCH /v1/agents/{agent_id}`

Body:

```json
{
  "description": "Updated grounded ops assistant",
  "default_mode": "instant",
  "allowed_modes": ["auto", "instant"]
}
```

Expected:

- updated agent

`POST /v1/agents/{agent_id}/datasets`

Body:

```json
{
  "dataset_id": "PASTE_DATASET_ID"
}
```

Expected:

- agent response with `dataset_ids` containing the dataset

### 3.7 Conversations

`POST /v1/agents/{agent_id}/conversations`

Body:

```json
{
  "title": "Advisor Demo Chat",
  "mode": "auto"
}
```

Expected:

- `201 Created`
- `conversation_id`
- `last_used_mode = "auto"`

Save `conversation_id`.

`GET /v1/agents/{agent_id}/conversations`

Expected:

- list includes the conversation

`GET /v1/conversations/{conversation_id}`

Expected:

- exact conversation resource

`PATCH /v1/conversations/{conversation_id}`

Body:

```json
{
  "title": "Advisor Demo Chat Updated",
  "mode": "instant"
}
```

Expected:

- updated conversation
- `last_used_mode = "instant"`

### 3.8 Agent Chat

`POST /v1/agents/{agent_id}/chat`

Body:

```json
{
  "conversation_id": "PASTE_CONVERSATION_ID",
  "message": "What is the maintenance window?",
  "mode": "auto",
  "dataset_id": "PASTE_DATASET_ID"
}
```

Expected:

- `200 OK`
- `answer`
- `citations`
- `confidence_score`
- `verification_status`
- `run_id`

Expected response headers:

- `X-Run-Id`
- `X-Trace-Id`

With the sample upload, the answer should be close to:

```json
{
  "answer": "Maintenance window: Friday at 22:00 UTC. [E001]"
}
```

Negative test:

Use:

```json
{
  "conversation_id": "PASTE_CONVERSATION_ID",
  "message": "Use a deeper mode",
  "mode": "thinking",
  "dataset_id": "PASTE_DATASET_ID"
}
```

Expected:

- `422`
- detail that `thinking` is not available yet

### 3.9 Messages and Runs

`GET /v1/conversations/{conversation_id}/messages`

Expected:

- at least 2 messages
- one `user`
- one `assistant`

`GET /v1/runs`

Expected:

- newest-first run list
- most recent run is your chat turn

`GET /v1/runs/{run_id}`

Expected:

- `query`
- `answer`
- `citations`
- `selected_mode`
- `effective_tier = "standard"`
- `routing_reason`

### 3.10 Dashboard

`GET /v1/dashboard/summary`

Expected fields:

- `dataset_count`
- `document_count`
- `indexed_document_count`
- `running_job_count`
- `failed_job_count`
- `agent_count`
- `conversation_count`

`GET /v1/dashboard/recent-runs`

Expected:

- run list containing the recent chat run

`GET /v1/dashboard/recent-jobs`

Expected:

- recent ingestion job list containing the uploaded document job

### 3.11 API Keys

`GET /v1/api-keys`

Expected:

- list of the current tenant’s API keys

`POST /v1/api-keys`

Body:

```json
{
  "label": "swagger-test-key"
}
```

Expected:

- `201 Created`
- `key_id`
- `api_key`
- raw `api_key` is returned exactly once

Save the returned `key_id`.

`POST /v1/api-keys/{key_id}/revoke`

Expected:

- revoked key metadata
- `revoked_at` is now populated

Do not revoke the key you are currently using in Swagger.

### 3.12 Optional Legacy Standard Endpoints

These still exist and should continue to work:

`POST /v1/documents/upload`

Use `multipart/form-data`:

- `namespace_id`
- `title`
- `file`

Expected:

- same upload behavior as dataset upload
- duplicate content in the same dataset/namespace returns `200` with `already_exists = true`

`POST /v1/query`

Body:

```json
{
  "namespace_id": "PASTE_DATASET_ID",
  "query": "What is the maintenance window?"
}
```

Expected:

- grounded answer with citations
- `X-Trace-Id` response header

## 4. Reviewer Summary

If all of the steps above pass, the current backend is behaving correctly for:

- Standard ingestion and query
- Phase 1.5 product-shell APIs
- API-key login flow
- dataset-backed agent chat
- run history and dashboard inspection
- idempotent duplicate uploads within one dataset
