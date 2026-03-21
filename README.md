# Grounded Backend

Grounded is a managed Retrieval-Augmented Generation platform for user-owned
documents. Users upload supported files, receive API and dashboard access, and
query their own knowledge base without building chunking, embeddings,
retrieval, or verification pipelines themselves.

This repository contains the backend foundation and architecture docs for that
platform.

## Architecture Summary

Grounded is designed around one core rule:

- data belongs to a **tenant** and **namespace**
- queries are routed to an **effective execution tier**

The platform is intentionally built around four separate concepts:

- **subscription plans**: what a customer is allowed to use
- **execution tiers**: how deeply a specific query is processed
- **namespace policy**: dataset-level safety and routing rules
- **runtime routing**: how the system chooses the final tier for a query

This separation is what lets Grounded stay fast on simple questions while still
escalating to deeper retrieval or verification when the query or dataset
requires it.

## Plans Vs Tiers

Grounded keeps user-facing plans separate from internal execution tiers.

### Subscription plans

These are commercial and entitlement concepts:

- Free Plan
- Pro Plan
- Business Plan
- Enterprise Plan

They control things like quotas, storage, and which execution tiers a tenant is
allowed to use.

### Execution tiers

These are runtime modes:

- **Standard**: fast, production-grade baseline RAG
- **Enterprise**: stronger retrieval precision
- **Critical**: highest-assurance verification path

The default experience should be `Auto (Recommended)`, with manual tier
selection only when the user's plan allows it.

## What Each Execution Tier Includes

### Standard

Standard is the strong baseline Grounded builds first. It includes:

- tenant and namespace isolation
- deterministic chunking
- sparse + dense hybrid retrieval
- Reciprocal Rank Fusion (RRF)
- evidence packaging
- grounded generation
- structured citations
- degraded responses instead of unsupported claims
- query traces

Standard does **not** enable planner, reranking, semantic chunking, web
fallback, internal model retrieval, or the critic loop by default.

### Enterprise

Enterprise includes everything in Standard, plus:

- planner for eligible complex queries
- temporal and freshness scoring
- reranking
- stronger evidence selection
- semantic chunking as a controlled upgrade path

### Critical

Critical includes everything in Enterprise, plus:

- verification / critic loop
- Corrective RAG with allowlisted web fallback
- internal model retrieval for selected corpora
- FreshPrompt conflict handling
- strongest degraded behavior
- async path for long-running high-assurance queries

## Why Grounded Is Stronger Than Basic RAG

Basic RAG is often just:

1. chunk documents
2. embed documents
3. run vector search
4. send top chunks to the model
5. answer

Grounded Standard is stronger because it adds multitenant isolation, hybrid
retrieval, citation-aware evidence packaging, structured output, degraded
behavior, and traceability. Enterprise and Critical then add more retrieval
precision and higher-assurance verification on top of that baseline.

## Key Documents

- `docs/SOLUTION_ARCHITECTURE.md`: canonical product and capability model
- `docs/SYSTEM_DESIGN.md`: product model, runtime flow, routing, and tier activation
- `docs/IMPLEMENTATION_PLAN.md`: delivery phases from foundation to Critical tier
- `docs/ENGINEERING_GUARDRAILS.md`: rules that keep implementation aligned with the architecture
- `docs/BRIEF.md`: overview of the solution and roadmap
- `docs/proposal.md`: project proposal
- `docs/ARP.md`: academic / project report draft

## What Problem It Solves

Basic RAG systems often fail when retrieval quality is weak, queries are
ambiguous, or answers are generated without enough trust controls. Grounded
addresses those weaknesses by combining adaptive retrieval, query handling,
verification, and traceable evidence into one platform.

## What Grounded Provides

- document ingestion for supported text-based files such as PDF, DOCX, and TXT
- automatic parsing, chunking, embedding, and indexing
- hybrid lexical and semantic retrieval
- reranking and adaptive processing depth in higher tiers
- grounded answer generation with citations
- provenance and traceability for responses
- API-based access for developers
- dashboard-based access for end users and operators

## Repository Scope

This repository contains the backend foundation for the platform: service code,
infrastructure definitions, migrations, and tests. The full product includes
API access and a dashboard, but this codebase is focused on the backend first.

## Prerequisites

Install these before starting:

- Python 3.11+
- Docker Desktop
- Git
- Git Bash

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Grounded-RAG/grounding-engine.git
cd grounding-engine
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

```bash
source .venv/Scripts/activate
```

### 4. Install backend dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

All Python commands below assume this virtual environment is still active.

### 5. Create the local environment file

```bash
cp .env.example .env
```

If `.env` already exists, update it instead of overwriting it.

Some values in `.env.example` are intentionally reserved for later phases, such
as Redis, Qdrant, provider keys, and external telemetry settings. The current
Phase 0 backend actively uses the app, database, storage, and `API_KEY_SALT`
settings.

### 6. Start local infrastructure

This starts PostgreSQL, Redis, Qdrant, and MinIO:

```bash
docker compose up -d postgres redis qdrant minio
```

### 7. Run the backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The API should start on `http://localhost:8000`.

## Testing the Current Backend

### Run the current test suite

Before running integration tests against a fresh local database, apply the
Alembic migrations:

```bash
cd backend
python -m alembic upgrade head
cd ..
```

From the repository root:

```bash
python -m pytest backend/tests/unit/test_config.py backend/tests/unit/test_database.py backend/tests/unit/test_alembic_config.py backend/tests/unit/test_models.py backend/tests/unit/test_security.py backend/tests/unit/test_storage.py backend/tests/integration/test_health.py backend/tests/integration/test_auth.py backend/tests/integration/test_telemetry.py
```

### Verify the API manually

With the backend running in one Git Bash window, test these endpoints in another:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Expected behavior:

- `/` returns service metadata
- `/health/live` returns `{"status":"alive"}`
- `/health/ready` returns readiness information for config, database, and storage

## Useful Commands

Start infrastructure:

```bash
docker compose up -d postgres redis qdrant minio
```

Stop infrastructure:

```bash
docker compose down
```

Run the backend from the repository root:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Run all backend tests:

```bash
cd backend
pytest
```

Run the compile check:

```bash
python -m compileall backend/app backend/tests backend/alembic
```

Run the migration smoke check:

```bash
cd backend
python -m alembic upgrade head
python -m alembic current
python -m alembic downgrade base
python -m alembic upgrade head
python -m alembic heads
```

Run the full foundation gate used by CI:

```bash
python -m compileall backend/app backend/tests backend/alembic
cd backend
python -m alembic upgrade head
python -m alembic current
python -m alembic downgrade base
python -m alembic upgrade head
python -m alembic heads
cd ..
python -m pytest backend/tests/unit/test_config.py backend/tests/unit/test_database.py backend/tests/unit/test_alembic_config.py backend/tests/unit/test_models.py backend/tests/unit/test_security.py backend/tests/unit/test_storage.py backend/tests/integration/test_health.py backend/tests/integration/test_auth.py backend/tests/integration/test_telemetry.py
```

If `make` is available on your machine, the same workflow is also exposed through `make compile`, `make migrate-check`, `make test-foundation`, and `make ci`.

## Local Service Ports

- Backend API: `8000`
- PostgreSQL: `5433`
- Redis: `6379`
- Qdrant: `6333`
- MinIO API: `9000`
- MinIO Console: `9001`

## Repository Layout

```text
grounding-engine/
|-- .github/workflows/        # CI workflows
|-- backend/
|   |-- alembic/              # Migration environment and revision files
|   |-- app/
|   |   |-- api/              # HTTP routes and API dependencies
|   |   |-- core/             # Infrastructure and shared components
|   |   |-- models/           # Persistence models
|   |   |-- pipeline/         # Query pipeline contracts and orchestration
|   |   |-- repositories/     # Data access layer
|   |   |-- schemas/          # Request and response schemas
|   |   |-- services/         # Business logic services
|   |   |-- workers/          # Background worker entrypoints
|   |   |-- config.py         # Runtime settings
|   |   `-- main.py           # FastAPI app entrypoint
|   |-- tests/                # Unit, integration, contract, evaluation, and load tests
|   |-- alembic.ini           # Alembic configuration
|   |-- Dockerfile            # Backend container image definition
|   `-- pyproject.toml        # Python project metadata and dependencies
|-- docs/                     # Solution, design, implementation, proposal, and guardrails
|-- .env.example              # Public environment template
|-- docker-compose.yml        # Local infrastructure services
|-- docker-compose.dev.yml    # Backend development stack
`-- Makefile                  # Common development commands
```
