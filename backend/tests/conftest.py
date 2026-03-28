"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import DuckDBService


DATA_DIR = "/Users/alejandromartinezmontoya/Documents/rappi/data"


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key-not-real",
        duckdb_data_dir=DATA_DIR,
    )


@pytest.fixture()
def db_service() -> DuckDBService:
    return DuckDBService(data_dir=DATA_DIR)


@pytest.fixture()
def test_client(db_service: DuckDBService) -> TestClient:
    from app.main import app
    from app.dependencies import get_db

    app.dependency_overrides[get_db] = lambda: db_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
