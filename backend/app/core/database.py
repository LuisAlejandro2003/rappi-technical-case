"""DuckDB service for loading and querying CSV data."""

import os
from pathlib import Path

import duckdb


class DuckDBService:
    def __init__(self, data_dir: str) -> None:
        self.conn = duckdb.connect(database=":memory:")
        self._load_all_csvs(data_dir)

    def _load_all_csvs(self, data_dir: str) -> None:
        data_path = Path(data_dir)
        if not data_path.is_absolute():
            # Resolve relative paths from the project root (two levels up from this file)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            candidate = project_root / data_path
            if candidate.exists():
                data_path = candidate
        for csv_file in sorted(data_path.glob("*.csv")):
            table_name = csv_file.stem.lower()
            self.load_csv(table_name, str(csv_file))

    def load_csv(self, table_name: str, file_path: str) -> None:
        self.conn.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}')"
        )

    def execute(self, sql: str) -> list[dict]:
        result = self.conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_table_names(self) -> list[str]:
        results = self.execute("SHOW TABLES")
        return [row["name"] for row in results]

    def get_row_counts(self) -> dict[str, int]:
        tables = self.get_table_names()
        counts = {}
        for table in tables:
            result = self.execute(f"SELECT COUNT(*) AS c FROM {table}")
            counts[table] = result[0]["c"]
        return counts

    def get_table_schema(self, table_name: str) -> list[dict]:
        results = self.execute(f"DESCRIBE {table_name}")
        return [
            {"column_name": row["column_name"], "column_type": row["column_type"]}
            for row in results
        ]
