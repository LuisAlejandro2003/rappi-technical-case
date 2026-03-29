import re

from app.models.schemas import Series, VizConfig

# Week column patterns and their labels
WEEK_COLUMNS_ROLL = [
    "L8W_ROLL", "L7W_ROLL", "L6W_ROLL", "L5W_ROLL",
    "L4W_ROLL", "L3W_ROLL", "L2W_ROLL", "L1W_ROLL", "L0W_ROLL",
]
WEEK_COLUMNS_ORDER = [
    "L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W",
]

WEEK_LABELS = [
    "Hace 8 sem", "Hace 7 sem", "Hace 6 sem", "Hace 5 sem",
    "Hace 4 sem", "Hace 3 sem", "Hace 2 sem", "Sem pasada", "Esta semana",
]


def map_week_labels(columns: list[str]) -> list[str]:
    """Map week column names to human-readable Spanish labels."""
    roll_map = dict(zip(WEEK_COLUMNS_ROLL, WEEK_LABELS))
    order_map = dict(zip(WEEK_COLUMNS_ORDER, WEEK_LABELS))
    merged = {**roll_map, **order_map}
    return [merged.get(col, col) for col in columns]


_TREND_PATTERNS = re.compile(
    r"\b(evolucion|tendencia|trend|over time|semana a semana|historico|temporal|evolución)\b",
    re.IGNORECASE,
)
_COMPARISON_PATTERNS = re.compile(
    r"\b(compara|compare|vs|versus|diferencia|difference)\b",
    re.IGNORECASE,
)
_RANKING_PATTERNS = re.compile(
    r"\b(top|ranking|mejores|peores|mayor|menor|best|worst)\b",
    re.IGNORECASE,
)


def determine_viz_type(question: str, result_data: list[dict]) -> str:
    """Determine the best visualization type based on question and data."""
    if len(result_data) == 1 and len(result_data[0]) <= 2:
        return "text"

    if _TREND_PATTERNS.search(question):
        return "line"
    if _COMPARISON_PATTERNS.search(question):
        return "bar"
    if _RANKING_PATTERNS.search(question):
        return "table"

    return "table"


def build_viz_config(
    viz_type: str,
    title: str,
    result_data: list[dict],
    question: str = "",
) -> VizConfig | None:
    """Build a VizConfig from query results."""
    if not result_data or viz_type == "text":
        return None

    columns = list(result_data[0].keys())

    if viz_type == "line":
        # Identify week columns for x-axis
        week_cols = [
            c for c in columns
            if c in WEEK_COLUMNS_ROLL or c in WEEK_COLUMNS_ORDER
        ]
        if not week_cols:
            # Fall back to table if no week columns
            return VizConfig(
                type="table", title=title, x_axis=columns,
                series=[], raw_data=result_data,
            )

        x_axis = map_week_labels(week_cols)

        # Each row becomes a series (e.g., each zone or metric)
        label_cols = [c for c in columns if c not in week_cols]
        series = []
        for row in result_data:
            label = " - ".join(
                str(row[c]) for c in label_cols if row.get(c) is not None
            )
            data = [row.get(wc) for wc in week_cols]
            series.append(Series(name=label or "Datos", data=data))

        return VizConfig(type="line", title=title, x_axis=x_axis, series=series)

    elif viz_type == "bar":
        # First string column as categories, numeric columns as series
        label_col = None
        value_cols = []
        for col in columns:
            sample_val = result_data[0].get(col)
            if isinstance(sample_val, (int, float)) and label_col is not None:
                value_cols.append(col)
            elif label_col is None and isinstance(sample_val, str):
                label_col = col
            elif isinstance(sample_val, (int, float)):
                value_cols.append(col)

        if not label_col or not value_cols:
            return VizConfig(
                type="table", title=title, x_axis=columns,
                series=[], raw_data=result_data,
            )

        x_axis = [str(row[label_col]) for row in result_data]
        series = []
        for vc in value_cols:
            data = [row.get(vc) for row in result_data]
            series.append(Series(name=vc, data=data))

        return VizConfig(type="bar", title=title, x_axis=x_axis, series=series)

    else:  # table
        return VizConfig(
            type="table", title=title, x_axis=columns,
            series=[], raw_data=result_data,
        )
