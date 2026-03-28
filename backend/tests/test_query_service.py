"""Tests for QueryService (schema context + query execution)."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.database import DuckDBService
from app.services.query_service import QueryService, build_schema_context, execute_query


class TestBuildSchemaContext:
    def test_returns_ddl_for_each_table(self, db_service: DuckDBService):
        context = build_schema_context(db_service)
        assert "raw_input_metrics" in context
        assert "raw_orders" in context
        assert "raw_summary" in context

    def test_includes_create_table(self, db_service: DuckDBService):
        context = build_schema_context(db_service)
        assert "CREATE TABLE" in context.upper() or "create table" in context.lower()

    def test_includes_sample_rows(self, db_service: DuckDBService):
        context = build_schema_context(db_service)
        # Should contain actual data values from the CSVs
        # raw_orders always has METRIC = "Orders"
        assert "Orders" in context

    def test_includes_metrics_dictionary(self, db_service: DuckDBService):
        context = build_schema_context(db_service)
        assert "Gross Profit UE" in context
        assert "Perfect Orders" in context
        assert "Pro Adoption" in context
        assert "Turbo Adoption" in context

    def test_includes_week_column_mapping(self, db_service: DuckDBService):
        context = build_schema_context(db_service)
        assert "L0W" in context
        assert "most recent" in context.lower() or "current" in context.lower()


class TestExecuteQuery:
    def test_returns_list_of_dicts(self, db_service: DuckDBService):
        results = execute_query(
            db_service,
            "SELECT COUNTRY, CITY FROM raw_orders LIMIT 3",
            timeout_seconds=5,
        )
        assert isinstance(results, list)
        assert len(results) == 3
        assert isinstance(results[0], dict)
        assert "COUNTRY" in results[0]

    def test_raises_on_invalid_sql(self, db_service: DuckDBService):
        with pytest.raises(Exception):
            execute_query(db_service, "SELECT FROM WHERE", timeout_seconds=5)

    def test_respects_timeout(self, db_service: DuckDBService):
        """Mock a slow query to test timeout behavior."""
        slow_db = MagicMock(spec=DuckDBService)

        def slow_execute(sql: str) -> list[dict]:
            time.sleep(10)
            return []

        slow_db.execute.side_effect = slow_execute

        with pytest.raises(TimeoutError):
            execute_query(slow_db, "SELECT * FROM raw_orders", timeout_seconds=1)


class TestQueryServiceIntegration:
    def test_validate_and_execute_valid_query(self, db_service: DuckDBService, mock_settings: Settings):
        qs = QueryService(db_service, mock_settings)
        results = qs.validate_and_execute("SELECT COUNTRY FROM raw_orders LIMIT 5")
        assert isinstance(results, list)
        assert len(results) == 5

    def test_validate_and_execute_rejects_bad_table(self, db_service: DuckDBService, mock_settings: Settings):
        qs = QueryService(db_service, mock_settings)
        with pytest.raises(ValueError, match="(?i)table"):
            qs.validate_and_execute("SELECT * FROM evil_table")

    def test_get_schema_context(self, db_service: DuckDBService, mock_settings: Settings):
        qs = QueryService(db_service, mock_settings)
        context = qs.get_schema_context()
        assert "raw_input_metrics" in context
        assert "raw_orders" in context

    def test_allowed_tables_populated(self, db_service: DuckDBService, mock_settings: Settings):
        qs = QueryService(db_service, mock_settings)
        assert "raw_input_metrics" in qs.allowed_tables
        assert "raw_orders" in qs.allowed_tables

    def test_allowed_columns_populated(self, db_service: DuckDBService, mock_settings: Settings):
        qs = QueryService(db_service, mock_settings)
        assert "COUNTRY" in qs.allowed_columns["raw_orders"]
        assert "METRIC" in qs.allowed_columns["raw_orders"]
