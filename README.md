# grounding-engine

Backend-first repository for Grounded, a reliability-focused adaptive RAG platform.

This repository is intentionally scoped to the backend for now. The frontend will live in a separate milestone later, so the initial structure only prepares the backend service, local infrastructure, migrations, tests, and CI.

## Current structure

```text
grounding-engine/
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- backend/
|   |-- alembic/
|   |   |-- versions/
|   |   |   `-- .gitkeep
|   |   `-- env.py
|   |-- app/
|   |   |-- api/
|   |   |   |-- deps.py
|   |   |   `-- v1/
|   |   |       |-- auth.py
|   |   |       |-- health.py
|   |   |       `-- router.py
|   |   |-- core/
|   |   |-- models/
|   |   |-- pipeline/
|   |   |   `-- stages/
|   |   |-- repositories/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- workers/
|   |   |-- config.py
|   |   `-- main.py
|   |-- tests/
|   |   |-- contract/
|   |   |-- evaluation/
|   |   |-- integration/
|   |   |-- load/
|   |   `-- unit/
|   |-- alembic.ini
|   |-- Dockerfile
|   `-- pyproject.toml
|-- docs/
|-- .env.example
|-- .gitignore
|-- docker-compose.dev.yml
|-- docker-compose.yml
`-- Makefile
```

## What this first milestone covers

- Backend-only folder structure
- Root project files for local infra, CI, and environment setup
- Python package layout for API, core infrastructure, domain layers, pipeline, workers, and tests
- Placeholder modules so the next milestone can add actual runtime behavior cleanly

## Next backend milestones

- FastAPI bootstrap, config loading, and health endpoints
- Database connection, Alembic wiring, and Phase 0 schema
- API key auth, tenant resolution, storage, and telemetry scaffolding
