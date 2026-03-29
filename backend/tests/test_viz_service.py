"""Tests for viz_service — written BEFORE implementation (TDD)."""

import pytest

from app.services.viz_service import (
    build_viz_config,
    determine_viz_type,
    map_week_labels,
)


# ---------------------------------------------------------------------------
# determine_viz_type
# ---------------------------------------------------------------------------

class TestDetermineVizType:
    """Classify the best chart type from question keywords + result shape."""

    @pytest.mark.parametrize("question", [
        "evolucion de ordenes por semana",
        "tendencia de ventas",
        "order trend last 8 weeks",
        "sales over time",
        "evolución del GMV",
    ])
    def test_trend_keywords_return_line(self, question: str):
        data = [{"zone": "BOG", "L8W_ROLL": 1, "L0W_ROLL": 2}]
        assert determine_viz_type(question, data) == "line"

    @pytest.mark.parametrize("question", [
        "compara las zonas",
        "compare bogota vs medellin",
        "diferencia entre zonas",
        "bogota versus medellin",
    ])
    def test_comparison_keywords_return_bar(self, question: str):
        data = [{"zone": "BOG", "orders": 100}, {"zone": "MDE", "orders": 80}]
        assert determine_viz_type(question, data) == "bar"

    @pytest.mark.parametrize("question", [
        "top 10 tiendas",
        "ranking de zonas",
        "mejores restaurantes",
        "peores zonas por cancelacion",
    ])
    def test_ranking_keywords_return_table(self, question: str):
        data = [{"store": "A", "orders": 100}, {"store": "B", "orders": 80}]
        assert determine_viz_type(question, data) == "table"

    def test_single_value_result_returns_text(self):
        """A single row with <= 2 columns is a scalar answer, no chart needed."""
        data = [{"total_orders": 42}]
        assert determine_viz_type("cuantas ordenes hubo", data) == "text"

    def test_single_row_two_cols_returns_text(self):
        data = [{"metric": "orders", "value": 42}]
        assert determine_viz_type("cuantas ordenes hubo", data) == "text"

    def test_defaults_to_table_for_unknown(self):
        data = [{"a": 1, "b": 2, "c": 3}]
        assert determine_viz_type("dame los datos", data) == "table"


# ---------------------------------------------------------------------------
# map_week_labels
# ---------------------------------------------------------------------------

class TestMapWeekLabels:
    def test_roll_columns(self):
        cols = ["L8W_ROLL", "L4W_ROLL", "L0W_ROLL"]
        labels = map_week_labels(cols)
        assert labels == ["Hace 8 sem", "Hace 4 sem", "Esta semana"]

    def test_order_columns(self):
        cols = ["L8W", "L7W", "L0W"]
        labels = map_week_labels(cols)
        assert labels == ["Hace 8 sem", "Hace 7 sem", "Esta semana"]

    def test_unknown_columns_pass_through(self):
        cols = ["zone", "L0W_ROLL"]
        labels = map_week_labels(cols)
        assert labels == ["zone", "Esta semana"]


# ---------------------------------------------------------------------------
# build_viz_config
# ---------------------------------------------------------------------------

class TestBuildVizConfig:
    def test_line_chart_weekly_data(self):
        data = [
            {"zone": "BOG", "L8W_ROLL": 100, "L7W_ROLL": 110, "L0W_ROLL": 150},
            {"zone": "MDE", "L8W_ROLL": 80, "L7W_ROLL": 85, "L0W_ROLL": 95},
        ]
        cfg = build_viz_config("line", "Ordenes por semana", data)
        assert cfg is not None
        assert cfg.type == "line"
        assert cfg.x_axis == ["Hace 8 sem", "Hace 7 sem", "Esta semana"]
        assert len(cfg.series) == 2
        assert cfg.series[0].name == "BOG"
        assert cfg.series[0].data == [100, 110, 150]
        assert cfg.series[1].name == "MDE"

    def test_bar_chart(self):
        data = [
            {"zone": "BOG", "orders": 500},
            {"zone": "MDE", "orders": 300},
        ]
        cfg = build_viz_config("bar", "Ordenes por zona", data)
        assert cfg is not None
        assert cfg.type == "bar"
        assert cfg.x_axis == ["BOG", "MDE"]
        assert len(cfg.series) == 1
        assert cfg.series[0].name == "orders"
        assert cfg.series[0].data == [500, 300]

    def test_table_returns_raw_data(self):
        data = [
            {"store": "A", "orders": 10, "gmv": 1000},
            {"store": "B", "orders": 5, "gmv": 500},
        ]
        cfg = build_viz_config("table", "Top tiendas", data)
        assert cfg is not None
        assert cfg.type == "table"
        assert cfg.raw_data == data
        assert cfg.x_axis == ["store", "orders", "gmv"]

    def test_empty_data_returns_none(self):
        cfg = build_viz_config("bar", "Empty", [])
        assert cfg is None

    def test_text_type_returns_none(self):
        cfg = build_viz_config("text", "Scalar", [{"total": 42}])
        assert cfg is None

    def test_line_chart_with_order_week_columns(self):
        """L8W, L7W, ... columns (orders table) should also work for line charts."""
        data = [
            {"zone": "BOG", "L8W": 100, "L0W": 150},
        ]
        cfg = build_viz_config("line", "Ordenes", data)
        assert cfg is not None
        assert cfg.type == "line"
        assert cfg.x_axis == ["Hace 8 sem", "Esta semana"]
        assert cfg.series[0].data == [100, 150]
