.PHONY: infra-up infra-down backend-run test lint format migrate tree

infra-up:
	docker compose up -d postgres redis qdrant minio

infra-down:
	docker compose down

backend-run:
	cd backend && python -m uvicorn app.main:app --reload

test:
	cd backend && pytest

lint:
	cd backend && python -m compileall app tests

format:
	@echo "Formatting will be added in the next milestone."

migrate:
	cd backend && alembic upgrade head

tree:
	@echo "Use your IDE file explorer or 'Get-ChildItem -Recurse' to inspect the repo tree."
