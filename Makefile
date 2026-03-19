.PHONY: infra-up infra-down backend-run test test-foundation compile migrate migrate-check ci format tree

infra-up:
	docker compose up -d postgres redis qdrant minio

infra-down:
	docker compose down

backend-run:
	cd backend && python -m uvicorn app.main:app --reload

test:
	cd backend && pytest

test-foundation:
	python -m pytest backend/tests/unit/test_config.py backend/tests/unit/test_database.py backend/tests/unit/test_alembic_config.py backend/tests/unit/test_models.py backend/tests/unit/test_security.py backend/tests/unit/test_storage.py backend/tests/integration/test_health.py backend/tests/integration/test_auth.py backend/tests/integration/test_telemetry.py

compile:
	python -m compileall backend/app backend/tests

lint: compile

migrate:
	cd backend && python -m alembic upgrade head

migrate-check:
	cd backend && python -m alembic upgrade head
	cd backend && python -m alembic current
	cd backend && python -m alembic downgrade base
	cd backend && python -m alembic upgrade head
	cd backend && python -m alembic heads

ci: compile migrate-check test-foundation

format:
	@echo "Formatting will be added in a later milestone."

tree:
	@echo "Use your IDE file explorer or 'Get-ChildItem -Recurse' to inspect the repo tree."
