"""Tests for SQL validation in query_service."""

import pytest

from app.services.query_service import validate_sql


ALLOWED_TABLES = ["raw_input_metrics", "raw_orders", "raw_summary"]

ALLOWED_COLUMNS = {
    "raw_input_metrics": [
        "COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION",
        "METRIC", "L8W_ROLL", "L7W_ROLL", "L6W_ROLL", "L5W_ROLL",
        "L4W_ROLL", "L3W_ROLL", "L2W_ROLL", "L1W_ROLL", "L0W_ROLL",
    ],
    "raw_orders": [
        "COUNTRY", "CITY", "ZONE", "METRIC",
        "L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W",
    ],
    "raw_summary": ["Column", "Type", "Examples", "Description (inferred)"],
}

MAX_ROWS = 1000


class TestValidSelectStatements:
    def test_simple_select_passes(self):
        sql = "SELECT COUNTRY, CITY FROM raw_input_metrics LIMIT 10"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "SELECT" in result.upper()

    def test_select_star_passes(self):
        sql = "SELECT * FROM raw_orders LIMIT 5"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert result is not None

    def test_select_with_where(self):
        sql = "SELECT COUNTRY, CITY FROM raw_input_metrics WHERE COUNTRY = 'CO' LIMIT 10"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "WHERE" in result.upper()

    def test_select_with_aggregation(self):
        sql = "SELECT COUNTRY, COUNT(*) FROM raw_orders GROUP BY COUNTRY LIMIT 10"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "GROUP BY" in result.upper()


class TestDangerousStatementsRejected:
    def test_insert_rejected(self):
        with pytest.raises(ValueError, match="(?i)select"):
            validate_sql(
                "INSERT INTO raw_orders VALUES ('CO','Bogota','Z','Orders',1,2,3,4,5,6,7,8,9)",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_update_rejected(self):
        with pytest.raises(ValueError, match="(?i)select"):
            validate_sql(
                "UPDATE raw_orders SET L0W = 0",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_delete_rejected(self):
        with pytest.raises(ValueError, match="(?i)select"):
            validate_sql(
                "DELETE FROM raw_orders",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_drop_table_rejected(self):
        with pytest.raises(ValueError, match="(?i)select"):
            validate_sql(
                "DROP TABLE raw_orders",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_create_table_rejected(self):
        with pytest.raises(ValueError, match="(?i)select"):
            validate_sql(
                "CREATE TABLE evil (id INT)",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestMultiStatementRejected:
    def test_semicolon_multi_statement_rejected(self):
        with pytest.raises(ValueError, match="(?i)single"):
            validate_sql(
                "SELECT * FROM raw_orders; DROP TABLE raw_orders",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestInvalidTableRejected:
    def test_unknown_table_rejected(self):
        with pytest.raises(ValueError, match="(?i)table"):
            validate_sql(
                "SELECT * FROM users LIMIT 10",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_system_table_rejected(self):
        with pytest.raises(ValueError, match="(?i)table"):
            validate_sql(
                "SELECT * FROM information_schema.tables LIMIT 10",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestInvalidColumnRejected:
    def test_unknown_column_rejected(self):
        with pytest.raises(ValueError, match="(?i)column"):
            validate_sql(
                "SELECT password FROM raw_input_metrics LIMIT 10",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_unknown_column_in_where_rejected(self):
        with pytest.raises(ValueError, match="(?i)column"):
            validate_sql(
                "SELECT COUNTRY FROM raw_input_metrics WHERE secret = 'x' LIMIT 10",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestLimitEnforcement:
    def test_limit_added_when_missing(self):
        sql = "SELECT COUNTRY FROM raw_input_metrics"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "LIMIT" in result.upper()
        assert str(MAX_ROWS) in result

    def test_limit_capped_when_exceeds_max(self):
        sql = "SELECT COUNTRY FROM raw_input_metrics LIMIT 5000"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "LIMIT" in result.upper()
        # The limit in the result should be MAX_ROWS, not 5000
        assert "5000" not in result
        assert str(MAX_ROWS) in result

    def test_limit_preserved_when_within_max(self):
        sql = "SELECT COUNTRY FROM raw_input_metrics LIMIT 50"
        result = validate_sql(sql, ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS)
        assert "50" in result


class TestDuckDBExtensionsBlocked:
    def test_load_blocked(self):
        with pytest.raises(ValueError):
            validate_sql(
                "LOAD httpfs",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_install_blocked(self):
        with pytest.raises(ValueError):
            validate_sql(
                "INSTALL httpfs",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestCopyRejected:
    def test_copy_rejected(self):
        with pytest.raises(ValueError):
            validate_sql(
                "COPY raw_orders TO '/tmp/data.csv'",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )


class TestCommentsRejected:
    def test_line_comments_rejected(self):
        with pytest.raises(ValueError, match="(?i)comment"):
            validate_sql(
                "SELECT * FROM raw_orders -- this is a comment",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )

    def test_block_comments_rejected(self):
        with pytest.raises(ValueError, match="(?i)comment"):
            validate_sql(
                "SELECT * FROM raw_orders /* block comment */",
                ALLOWED_TABLES, ALLOWED_COLUMNS, MAX_ROWS,
            )
