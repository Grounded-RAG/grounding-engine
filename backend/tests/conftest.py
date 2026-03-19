"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with a fresh settings cache."""

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
