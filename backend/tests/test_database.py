"""Tests for DuckDBService — written BEFORE implementation (TDD red phase)."""

import pytest

from app.core.database import DuckDBService


class TestDuckDBServiceLoadCSVs:
    """Verify that DuckDBService loads CSV files correctly."""

    def test_tables_exist(self, db_service: DuckDBService):
        tables = db_service.get_table_names()
        assert "raw_input_metrics" in tables
        assert "raw_orders" in tables
        assert "raw_summary" in tables

    def test_row_counts_positive(self, db_service: DuckDBService):
        counts = db_service.get_row_counts()
        for table, count in counts.items():
            assert count > 0, f"Table {table} has 0 rows"

    def test_row_counts_keys_match_tables(self, db_service: DuckDBService):
        tables = set(db_service.get_table_names())
        counts_keys = set(db_service.get_row_counts().keys())
        assert tables == counts_keys


class TestDuckDBServiceExecute:
    """Verify execute() returns valid results."""

    def test_simple_select(self, db_service: DuckDBService):
        results = db_service.execute("SELECT 1 AS val")
        assert len(results) == 1
        assert results[0]["val"] == 1

    def test_select_from_table(self, db_service: DuckDBService):
        results = db_service.execute("SELECT * FROM raw_input_metrics LIMIT 5")
        assert len(results) == 5
        assert isinstance(results[0], dict)

    def test_connection_reusable(self, db_service: DuckDBService):
        r1 = db_service.execute("SELECT COUNT(*) AS c FROM raw_orders")
        r2 = db_service.execute("SELECT COUNT(*) AS c FROM raw_orders")
        assert r1[0]["c"] == r2[0]["c"]


class TestDuckDBServiceSchema:
    """Verify table schemas have expected columns."""

    def test_raw_input_metrics_columns(self, db_service: DuckDBService):
        schema = db_service.get_table_schema("raw_input_metrics")
        col_names = [col["column_name"] for col in schema]
        assert "COUNTRY" in col_names
        assert "CITY" in col_names
        assert "ZONE" in col_names

    def test_raw_orders_columns(self, db_service: DuckDBService):
        schema = db_service.get_table_schema("raw_orders")
        col_names = [col["column_name"] for col in schema]
        # raw_orders should have at least some columns
        assert len(col_names) > 0

    def test_schema_returns_list_of_dicts(self, db_service: DuckDBService):
        schema = db_service.get_table_schema("raw_summary")
        assert isinstance(schema, list)
        assert all(isinstance(col, dict) for col in schema)
        assert all("column_name" in col for col in schema)
        assert all("column_type" in col for col in schema)
