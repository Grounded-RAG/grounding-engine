# Grounded Backend

Grounded is a managed Retrieval-Augmented Generation platform for user-owned documents. Users upload supported files, receive API and dashboard access, and query their own knowledge base without building chunking, embeddings, retrieval, or verification pipelines themselves.

Grounded is being built as a platform product:

- users provide documents and knowledge sources
- the system ingests, chunks, indexes, retrieves, reranks, verifies, and answers
- answers are returned with citations and provenance
- access is provided through a dashboard and API keys

## What Problem It Solves

Basic RAG systems often fail when retrieval quality is weak, queries are ambiguous, or answers are generated without enough trust controls. Grounded addresses those weaknesses by combining adaptive retrieval, query handling, verification, and traceable evidence into one platform.

## What Grounded Provides

- document ingestion for supported text-based files such as PDF, DOCX, and TXT
- automatic parsing, chunking, embedding, and indexing
- hybrid lexical and semantic retrieval
- reranking and adaptive processing depth
- grounded answer generation with citations
- provenance and traceability for responses
- API-based access for developers
- dashboard-based access for end users and operators

## Repository Scope

This repository contains the backend foundation for the platform: service code, infrastructure definitions, migrations, and tests. The full product includes API access and a dashboard, but this codebase is focused on the backend first.

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

### 5. Create the local environment file

```bash
cp .env.example .env
```

If `.env` already exists, update it instead of overwriting it.

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

From the repository root:

```bash
python -m pytest backend/tests/unit/test_config.py backend/tests/integration/test_health.py
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
- `/health/ready` returns readiness information including config status

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
python -m compileall backend/app backend/tests
```

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
|-- docs/                     # Proposal, architecture, implementation, and guardrails
|-- .env.example              # Public environment template
|-- docker-compose.yml        # Local infrastructure services
|-- docker-compose.dev.yml    # Backend development stack
`-- Makefile                  # Common development commands
```

## Key Documents

- `docs/proposal.md` explains the problem, goal, scope, and product direction
- `docs/SYSTEM_DESIGN.md` defines the architecture and service boundaries
- `docs/IMPLEMENTATION_PLAN.md` defines the implementation phases
- `docs/ENGINEERING_GUARDRAILS.md` defines coding, testing, and release standards
