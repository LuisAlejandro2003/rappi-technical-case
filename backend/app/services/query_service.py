"""SQL validation, schema context building, and query execution service."""

from __future__ import annotations

import re
import threading
from typing import Any

import sqlglot
from sqlglot import exp

from app.core.config import Settings
from app.core.database import DuckDBService

# ---------------------------------------------------------------------------
# Metrics dictionary (used in schema context for the LLM)
# ---------------------------------------------------------------------------

METRICS_DICTIONARY: dict[str, str] = {
    "% PRO Users Who Breakeven": "Usuarios Pro cuyo valor generado cubre membresia / Total Pro",
    "% Restaurants Sessions With Optimal Assortment": "Sesiones con min 40 restaurantes / Total sesiones",
    "Gross Profit UE": "Margen bruto / Total ordenes",
    "Lead Penetration": "Tiendas habilitadas / (leads + habilitadas + salidas)",
    "MLTV Top Verticals Adoption": "Usuarios con ordenes en multiples verticales / Total usuarios",
    "Non-Pro PTC > OP": "Conversion No Pro de checkout a order placed",
    "Perfect Orders": "Orders sin cancelaciones/defectos/demora / Total ordenes",
    "Pro Adoption": "Usuarios Pro / Total usuarios",
    "Restaurants Markdowns / GMV": "Descuentos restaurantes / GMV restaurantes",
    "Restaurants SS > ATC CVR": "Conversion restaurantes de select store a add to cart",
    "Restaurants SST > SS CVR": "Porcentaje de seleccionar restaurantes a seleccionar tienda",
    "Retail SST > SS CVR": "Porcentaje de seleccionar supermercados a seleccionar tienda",
    "Turbo Adoption": "Usuarios Turbo / Total usuarios con Turbo disponible",
}

# Dangerous keywords that should be rejected before parsing
_DANGEROUS_KEYWORDS_RE = re.compile(
    r"\b(LOAD|INSTALL|COPY)\b", re.IGNORECASE
)

# Comment patterns
_COMMENT_RE = re.compile(r"(--|/\*)")


# ---------------------------------------------------------------------------
# validate_sql
# ---------------------------------------------------------------------------

def validate_sql(
    sql: str,
    allowed_tables: list[str],
    allowed_columns: dict[str, list[str]],
    max_rows: int,
) -> str:
    """Validate and sanitize a SQL string for safe read-only execution.

    Returns the (possibly modified) SQL string on success.
    Raises ValueError on any violation.
    """
    # ---- Step 0: reject comments ----
    if _COMMENT_RE.search(sql):
        raise ValueError("SQL comments are not allowed.")

    # ---- Step 1: reject dangerous keywords before parsing ----
    if _DANGEROUS_KEYWORDS_RE.search(sql):
        raise ValueError("Statements containing LOAD, INSTALL, or COPY are not allowed.")

    # ---- Step 2: parse with sqlglot ----
    try:
        expressions = sqlglot.parse(sql, dialect="duckdb")
    except Exception as exc:
        raise ValueError(f"Failed to parse SQL: {exc}") from exc

    # Filter out None expressions (sqlglot may return None for empty strings)
    expressions = [e for e in expressions if e is not None]

    if len(expressions) == 0:
        raise ValueError("Empty SQL statement.")

    if len(expressions) > 1:
        raise ValueError("Only a single SQL statement is allowed.")

    statement = expressions[0]

    # ---- Step 3: must be a SELECT ----
    if not isinstance(statement, exp.Select):
        raise ValueError("Only SELECT statements are allowed.")

    # ---- Step 4: reject subversive statement types that might parse as select ----
    for node in statement.walk():
        node_type = type(node).__name__
        if node_type in (
            "Insert", "Update", "Delete", "Drop", "Create",
            "Command", "Copy",
        ):
            raise ValueError("Only SELECT statements are allowed.")

    # ---- Step 5: validate table references ----
    allowed_tables_lower = {t.lower() for t in allowed_tables}
    for table_node in statement.find_all(exp.Table):
        table_name = table_node.name.lower()
        # Also check for schema-qualified names (e.g., information_schema.tables)
        if table_node.db:
            full_name = f"{table_node.db}.{table_name}"
            raise ValueError(
                f"Table '{full_name}' is not allowed. Allowed tables: {allowed_tables}"
            )
        if table_name not in allowed_tables_lower:
            raise ValueError(
                f"Table '{table_name}' is not allowed. Allowed tables: {allowed_tables}"
            )

    # ---- Step 6: validate column references ----
    # Build a set of all allowed columns across all referenced tables (case-insensitive)
    referenced_tables = []
    for table_node in statement.find_all(exp.Table):
        referenced_tables.append(table_node.name.lower())

    all_allowed_cols: set[str] = set()
    for tbl in referenced_tables:
        for t_key, cols in allowed_columns.items():
            if t_key.lower() == tbl:
                all_allowed_cols.update(c.upper() for c in cols)

    # Collect SELECT aliases so ORDER BY / HAVING can reference them
    select_aliases: set[str] = set()
    for sel_expr in statement.expressions:
        if isinstance(sel_expr, exp.Alias):
            select_aliases.add(sel_expr.alias.upper())

    # Only validate explicit column references (skip star, aliases, aggregations)
    for col_node in statement.find_all(exp.Column):
        col_name = col_node.name.upper()
        if col_name == "*":
            continue
        # Allow references to SELECT aliases (e.g. ORDER BY total_orders)
        if col_name in select_aliases:
            continue
        if col_name not in all_allowed_cols:
            raise ValueError(
                f"Column '{col_node.name}' is not allowed in the referenced tables."
            )

    # ---- Step 7: enforce LIMIT ----
    limit_node = statement.find(exp.Limit)
    if limit_node is None:
        statement = statement.limit(max_rows)
    else:
        # Extract the limit value
        limit_expr = limit_node.expression
        if isinstance(limit_expr, exp.Literal):
            limit_val = int(limit_expr.this)
            if limit_val > max_rows:
                limit_node.args["expression"] = exp.Literal.number(max_rows)

    return statement.sql(dialect="duckdb")


# ---------------------------------------------------------------------------
# build_schema_context
# ---------------------------------------------------------------------------

def build_schema_context(db: DuckDBService) -> str:
    """Build a schema context string for the LLM including DDL, samples, and metrics."""
    parts: list[str] = []

    tables = db.get_table_names()

    for table_name in tables:
        schema = db.get_table_schema(table_name)

        # DDL
        cols_ddl = ", ".join(
            f"{col['column_name']} {col['column_type']}" for col in schema
        )
        parts.append(f"CREATE TABLE {table_name} ({cols_ddl});")

        # Sample rows
        try:
            sample_rows = db.execute(f"SELECT * FROM {table_name} LIMIT 3")
            if sample_rows:
                parts.append(f"\n-- Sample rows from {table_name}:")
                for row in sample_rows:
                    parts.append(f"--   {row}")
        except Exception:
            pass

        parts.append("")

    # Metrics dictionary
    parts.append("## Metrics Dictionary")
    parts.append("| Metric | Description |")
    parts.append("|--------|-------------|")
    for metric, desc in METRICS_DICTIONARY.items():
        parts.append(f"| {metric} | {desc} |")
    parts.append("")

    # Week column mapping
    parts.append("## Week Column Mapping")
    parts.append(
        "For raw_input_metrics: L8W_ROLL = 8 weeks ago (oldest), "
        "L7W_ROLL = 7 weeks ago, ..., L1W_ROLL = 1 week ago, "
        "L0W_ROLL = most recent/current week."
    )
    parts.append(
        "For raw_orders: L8W = 8 weeks ago (oldest), "
        "L7W = 7 weeks ago, ..., L1W = 1 week ago, "
        "L0W = most recent/current week."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# execute_query
# ---------------------------------------------------------------------------

def execute_query(
    db: DuckDBService,
    sql: str,
    timeout_seconds: int,
) -> list[dict]:
    """Execute SQL against DuckDB with a timeout."""
    result_container: list[Any] = []
    error_container: list[Exception] = []

    def _run():
        try:
            result_container.append(db.execute(sql))
        except Exception as exc:
            error_container.append(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise TimeoutError(
            f"Query execution exceeded {timeout_seconds}s timeout."
        )

    if error_container:
        raise error_container[0]

    return result_container[0]


# ---------------------------------------------------------------------------
# QueryService
# ---------------------------------------------------------------------------

class QueryService:
    """Ties together validation, schema context, and execution."""

    def __init__(self, db: DuckDBService, settings: Settings):
        self.db = db
        self.settings = settings

        # Build allowed tables and columns from actual DB schema
        self.allowed_tables = db.get_table_names()
        self.allowed_columns: dict[str, list[str]] = {}
        for table in self.allowed_tables:
            schema = db.get_table_schema(table)
            self.allowed_columns[table] = [col["column_name"] for col in schema]

        # Cache schema context
        self._schema_context: str | None = None

    def validate_and_execute(self, sql: str) -> list[dict]:
        """Validate a SQL query and execute it."""
        validated_sql = validate_sql(
            sql,
            self.allowed_tables,
            self.allowed_columns,
            self.settings.max_result_rows,
        )
        return execute_query(
            self.db,
            validated_sql,
            self.settings.query_timeout_seconds,
        )

    def get_schema_context(self) -> str:
        """Return cached schema context string."""
        if self._schema_context is None:
            self._schema_context = build_schema_context(self.db)
        return self._schema_context
