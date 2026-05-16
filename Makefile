.PHONY: infra-up infra-down backend-run test test-foundation compile migrate migrate-check ci format tree benchmark-beir benchmark-beir-smoke

infra-up:
	docker compose up -d postgres redis qdrant minio

infra-down:
	docker compose down

backend-run:
	cd backend && python -m uvicorn app.main:app --reload --reload-dir app --reload-dir alembic --reload-exclude .venv/* --reload-exclude venv/* --reload-exclude vevn/*

test:
	cd backend && pytest

test-foundation:
	python -m pytest backend/tests/unit/test_config.py backend/tests/unit/test_database.py backend/tests/unit/test_alembic_config.py backend/tests/unit/test_models.py backend/tests/unit/test_security.py backend/tests/unit/test_storage.py backend/tests/integration/test_health.py backend/tests/integration/test_auth.py backend/tests/integration/test_telemetry.py

compile:
	python -m compileall backend/app backend/tests backend/alembic

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

benchmark-beir:
	cd backend && python -m tests.evaluation.benchmark_runner \
		--beir-dataset ../nfcorpus \
		--variants naive_dense_only,standard_hybrid,standard_no_rerank \
		--output reports/benchmark-beir-nfcorpus

benchmark-beir-smoke:
	cd backend && python -m tests.evaluation.benchmark_runner \
		--beir-dataset ../nfcorpus \
		--beir-limit 20 \
		--variants naive_dense_only,standard_hybrid,standard_no_rerank \
		--output reports/benchmark-beir-nfcorpus-smoke

format:
	@echo "Formatting will be added in a later milestone."

tree:
	@echo "Use your IDE file explorer or 'Get-ChildItem -Recurse' to inspect the repo tree."
