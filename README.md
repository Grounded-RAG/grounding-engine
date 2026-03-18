# Grounded Backend

Grounded is a managed Retrieval-Augmented Generation platform for user-owned documents. Users upload supported files, receive API and dashboard access, and query their own knowledge base without building chunking, embeddings, retrieval, or verification pipelines themselves.

The product direction is platform-first:

- users provide documents and knowledge sources
- the system ingests, chunks, indexes, retrieves, reranks, verifies, and answers
- answers are returned with citations and provenance
- access is provided through a dashboard and API keys

## What Problem It Solves

Basic RAG systems often fail when retrieval quality is weak, queries are ambiguous, or answers are generated without enough trust controls. Grounded is built to address those weaknesses by combining adaptive retrieval, query handling, verification, and traceable evidence into one platform.

## What Grounded Provides

- document ingestion for supported text-based files such as PDF, DOCX, and TXT
- automatic parsing, chunking, embedding, and indexing
- hybrid lexical and semantic retrieval
- reranking and adaptive processing depth
- grounded answer generation with citations
- provenance and traceability for responses
- API-based access for developers
- dashboard-based access for end users and operators

## Product Model

Grounded is being built as a platform product, not as a code package that users run themselves.

The intended flow is:

1. users upload documents or connect supported data sources
2. the platform processes and indexes that data
3. users query the system through the dashboard or API
4. the platform returns grounded answers over their uploaded data

In short:

Users bring the data, and Grounded provides the adaptive verified RAG system on top of that data.

## Repository Scope

This repository currently contains the backend foundation for that platform: service code, infrastructure definitions, migrations, and tests. The product includes API access and a dashboard, but this codebase is focused on the backend side first.

## Architecture Summary

- FastAPI for the API layer
- PostgreSQL for metadata and v1 sparse retrieval
- Qdrant for dense vector retrieval
- Redis for background jobs and queue-backed workflows
- MinIO or another S3-compatible service for document storage
- background workers for ingestion, extraction, indexing, and long-running tasks

The backend is designed around a staged pipeline that handles admission, retrieval, fusion, reranking, evidence packaging, generation, and verification.

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
