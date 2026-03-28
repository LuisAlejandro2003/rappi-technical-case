"""Tests for /health endpoint — written BEFORE implementation (TDD red phase)."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client: TestClient):
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, test_client: TestClient):
        data = test_client.get("/health").json()
        assert "status" in data
        assert "tables" in data
        assert "row_counts" in data

    def test_health_status_healthy(self, test_client: TestClient):
        data = test_client.get("/health").json()
        assert data["status"] == "healthy"

    def test_health_tables_include_expected(self, test_client: TestClient):
        data = test_client.get("/health").json()
        assert "raw_input_metrics" in data["tables"]
        assert "raw_orders" in data["tables"]

    def test_health_row_counts_is_dict(self, test_client: TestClient):
        data = test_client.get("/health").json()
        assert isinstance(data["row_counts"], dict)
        for table, count in data["row_counts"].items():
            assert isinstance(count, int)
            assert count > 0
