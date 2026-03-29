"""Tests for InsightsService — uses in-memory DuckDB with synthetic test data."""

from __future__ import annotations

import csv
import io
import os
import tempfile

import pytest

from app.core.database import DuckDBService
from app.models.schemas import Insight, InsightReport
from app.services.insights_service import InsightsService


# ------------------------------------------------------------------
# Test data helpers
# ------------------------------------------------------------------

def _write_csv(tmpdir: str, filename: str, rows: list[dict]) -> str:
    """Write a list of dicts to a CSV file and return the path."""
    path = os.path.join(tmpdir, filename)
    if not rows:
        # Write empty CSV with no rows
        with open(path, "w") as f:
            f.write("")
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _make_metric_row(
    country: str,
    city: str,
    zone: str,
    metric: str,
    *,
    l0w: float = 0.5,
    l1w: float = 0.5,
    l2w: float = 0.5,
    l3w: float = 0.5,
    l4w: float = 0.5,
    l5w: float = 0.5,
    l6w: float = 0.5,
    l7w: float = 0.5,
    l8w: float = 0.5,
) -> dict:
    return {
        "COUNTRY": country,
        "CITY": city,
        "ZONE": zone,
        "ZONE_TYPE": "Standard",
        "ZONE_PRIORITIZATION": "Prioritized",
        "METRIC": metric,
        "L8W_ROLL": l8w,
        "L7W_ROLL": l7w,
        "L6W_ROLL": l6w,
        "L5W_ROLL": l5w,
        "L4W_ROLL": l4w,
        "L3W_ROLL": l3w,
        "L2W_ROLL": l2w,
        "L1W_ROLL": l1w,
        "L0W_ROLL": l0w,
    }


def _make_order_row(
    country: str, city: str, zone: str, metric: str = "Orders",
    l0w: int = 100, l1w: int = 100,
) -> dict:
    return {
        "COUNTRY": country, "CITY": city, "ZONE": zone, "METRIC": metric,
        "L8W": l1w, "L7W": l1w, "L6W": l1w, "L5W": l1w,
        "L4W": l1w, "L3W": l1w, "L2W": l1w, "L1W": l1w, "L0W": l0w,
    }


def _make_summary_row() -> dict:
    return {"TABLE": "raw_input_metrics", "DESCRIPTION": "test"}


def _create_db(metric_rows: list[dict], order_rows: list[dict] | None = None) -> DuckDBService:
    """Create an in-memory DuckDB with test data."""
    tmpdir = tempfile.mkdtemp()
    _write_csv(tmpdir, "raw_input_metrics.csv", metric_rows)
    _write_csv(tmpdir, "raw_orders.csv", order_rows or [_make_order_row("CO", "Bogota", "Z1")])
    _write_csv(tmpdir, "raw_summary.csv", [_make_summary_row()])
    return DuckDBService(data_dir=tmpdir)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def basic_db() -> DuckDBService:
    """DB with enough zones per country (4) and a clear anomaly in Z1."""
    rows = [
        # Z1: big anomaly in Perfect Orders (0.8 -> 0.5 = -37.5%)
        _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders", l0w=0.5, l1w=0.8, l2w=0.78, l3w=0.75),
        # Z2-Z4: stable (peer group)
        _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.8, l1w=0.79, l2w=0.78, l3w=0.77),
        _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.81, l1w=0.80, l2w=0.79, l3w=0.78),
        _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.79, l1w=0.78, l2w=0.77, l3w=0.76),
    ]
    return _create_db(rows)


@pytest.fixture()
def trend_db() -> DuckDBService:
    """DB with clear 3-week declining trend for higher_is_better metric."""
    rows = [
        # Z1: declining 3 weeks in Perfect Orders (higher_is_better)
        _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders",
                         l0w=0.60, l1w=0.70, l2w=0.80, l3w=0.90),
        # Filler zones
        _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders",
                         l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
        _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders",
                         l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
        _make_metric_row("CO", "Cali", "Z4", "Perfect Orders",
                         l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
    ]
    return _create_db(rows)


@pytest.fixture()
def benchmark_db() -> DuckDBService:
    """DB where Z1 is far below peer median."""
    rows = [
        _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders", l0w=0.40),
        _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.80),
        _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.82),
        _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.78),
    ]
    return _create_db(rows)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestDetectAnomalies:
    def test_detects_large_wow_drop(self, basic_db: DuckDBService):
        svc = InsightsService(basic_db)
        findings = svc.detect_anomalies()
        # Z1 had a -37.5% drop — should be flagged
        z1_findings = [f for f in findings if f.zone == "Z1"]
        assert len(z1_findings) >= 1
        assert z1_findings[0].category == "anomalias"
        assert z1_findings[0].direction == "deterioration"
        assert z1_findings[0].magnitude < 0  # negative change

    def test_stable_zones_not_flagged(self, basic_db: DuckDBService):
        svc = InsightsService(basic_db)
        findings = svc.detect_anomalies()
        # Z2 had only ~1.3% change — below threshold
        z2_findings = [f for f in findings if f.zone == "Z2"]
        assert len(z2_findings) == 0

    def test_zero_baseline_flagged(self):
        """When L1W = 0 and L0W != 0, flag with magnitude 1.0."""
        rows = [
            _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders", l0w=0.5, l1w=0.0),
            _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.8, l1w=0.8),
            _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.8, l1w=0.8),
            _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.8, l1w=0.8),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        findings = svc.detect_anomalies()
        z1 = [f for f in findings if f.zone == "Z1"]
        assert len(z1) >= 1
        assert z1[0].magnitude == 1.0


class TestDetectTrends:
    def test_detects_3_week_decline(self, trend_db: DuckDBService):
        svc = InsightsService(trend_db)
        findings = svc.detect_trends()
        z1_findings = [f for f in findings if f.zone == "Z1"]
        assert len(z1_findings) >= 1
        assert z1_findings[0].category == "tendencias"
        assert z1_findings[0].direction == "deterioration"

    def test_stable_zone_no_trend(self, trend_db: DuckDBService):
        svc = InsightsService(trend_db)
        findings = svc.detect_trends()
        z2_findings = [f for f in findings if f.zone == "Z2"]
        assert len(z2_findings) == 0

    def test_lower_is_better_increasing_is_bad(self):
        """For % Order Loss (lower_is_better), increasing values = deterioration."""
        rows = [
            _make_metric_row("CO", "Bogota", "Z1", "% Order Loss",
                             l0w=0.20, l1w=0.15, l2w=0.10, l3w=0.05),
            _make_metric_row("CO", "Bogota", "Z2", "% Order Loss", l0w=0.05, l1w=0.05, l2w=0.05, l3w=0.05),
            _make_metric_row("CO", "Medellin", "Z3", "% Order Loss", l0w=0.05, l1w=0.05, l2w=0.05, l3w=0.05),
            _make_metric_row("CO", "Cali", "Z4", "% Order Loss", l0w=0.05, l1w=0.05, l2w=0.05, l3w=0.05),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        findings = svc.detect_trends()
        z1 = [f for f in findings if f.zone == "Z1"]
        assert len(z1) >= 1
        assert z1[0].direction == "deterioration"


class TestDetectBenchmarking:
    def test_flags_underperformer(self, benchmark_db: DuckDBService):
        svc = InsightsService(benchmark_db)
        findings = svc.detect_benchmarking()
        z1_findings = [f for f in findings if f.zone == "Z1"]
        assert len(z1_findings) >= 1
        assert z1_findings[0].category == "benchmarking"
        # Z1 at 0.40 vs median ~0.80 → ~50% divergence
        assert z1_findings[0].magnitude > 0.20

    def test_above_median_not_flagged(self, benchmark_db: DuckDBService):
        """For higher_is_better, zones above median should not be flagged."""
        svc = InsightsService(benchmark_db)
        findings = svc.detect_benchmarking()
        z3_findings = [f for f in findings if f.zone == "Z3"]
        assert len(z3_findings) == 0


class TestDetectCorrelations:
    def test_detects_paired_underperformance(self):
        rows = [
            # Z1: both Lead Penetration and Restaurants SST > SS CVR below median
            _make_metric_row("CO", "Bogota", "Z1", "Lead Penetration", l0w=0.30),
            _make_metric_row("CO", "Bogota", "Z1", "Restaurants SST > SS CVR", l0w=0.30),
            # Peers with higher values
            _make_metric_row("CO", "Bogota", "Z2", "Lead Penetration", l0w=0.70),
            _make_metric_row("CO", "Bogota", "Z2", "Restaurants SST > SS CVR", l0w=0.70),
            _make_metric_row("CO", "Medellin", "Z3", "Lead Penetration", l0w=0.75),
            _make_metric_row("CO", "Medellin", "Z3", "Restaurants SST > SS CVR", l0w=0.75),
            _make_metric_row("CO", "Cali", "Z4", "Lead Penetration", l0w=0.72),
            _make_metric_row("CO", "Cali", "Z4", "Restaurants SST > SS CVR", l0w=0.72),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        findings = svc.detect_correlations()
        z1 = [f for f in findings if f.zone == "Z1"]
        assert len(z1) >= 1
        assert z1[0].category == "correlaciones"
        assert "Lead Penetration" in z1[0].metrics


class TestDetectOpportunities:
    def test_detects_improving_trend(self):
        """3 consecutive weeks of improvement for higher_is_better."""
        rows = [
            _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders",
                             l0w=0.90, l1w=0.80, l2w=0.70, l3w=0.60),
            _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
            _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
            _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.80, l1w=0.80, l2w=0.80, l3w=0.80),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        findings = svc.detect_opportunities()
        z1 = [f for f in findings if f.zone == "Z1" and f.direction == "improvement"]
        assert len(z1) >= 1
        assert z1[0].category == "oportunidades"


class TestGenerateReport:
    def test_produces_complete_report(self, basic_db: DuckDBService):
        svc = InsightsService(basic_db)
        report = svc.generate_report()
        assert isinstance(report, InsightReport)
        assert report.id.startswith("report_")
        assert isinstance(report.findings, list)
        assert isinstance(report.category_counts, dict)
        # All category keys should be present
        for cat in ("anomalias", "tendencias", "benchmarking", "correlaciones", "oportunidades"):
            assert cat in report.category_counts

    def test_sorted_by_severity_descending(self, basic_db: DuckDBService):
        svc = InsightsService(basic_db)
        report = svc.generate_report()
        if len(report.findings) >= 2:
            for i in range(len(report.findings) - 1):
                assert report.findings[i].severity >= report.findings[i + 1].severity

    def test_cached_report(self, basic_db: DuckDBService):
        svc = InsightsService(basic_db)
        assert svc.get_cached_report() is None
        report = svc.generate_report()
        assert svc.get_cached_report() is report


class TestHelpers:
    def test_classify_direction_higher_is_better(self):
        assert InsightsService._classify_direction("Perfect Orders", 0.1) == "improvement"
        assert InsightsService._classify_direction("Perfect Orders", -0.1) == "deterioration"

    def test_classify_direction_lower_is_better(self):
        assert InsightsService._classify_direction("% Order Loss", -0.1) == "improvement"
        assert InsightsService._classify_direction("% Order Loss", 0.1) == "deterioration"

    def test_get_polarity_known(self):
        assert InsightsService._get_polarity("Perfect Orders") == "higher_is_better"
        assert InsightsService._get_polarity("% Order Loss") == "lower_is_better"

    def test_get_polarity_unknown_defaults(self):
        assert InsightsService._get_polarity("SomeUnknownMetric") == "higher_is_better"

    def test_build_explore_query_anomaly(self):
        q = InsightsService._build_explore_query(
            "anomalias", zone="Z1", country="CO", metric="PO", magnitude=15.3,
        )
        assert "Z1" in q
        assert "CO" in q
        assert "15.3" in q


class TestEdgeCases:
    def test_no_findings_empty_data(self):
        """Minimal data with no anomalies should produce empty lists."""
        rows = [
            _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        assert svc.detect_anomalies() == []
        assert svc.detect_trends() == []

    def test_report_with_no_findings(self):
        """Report should still be valid even with 0 findings."""
        rows = [
            _make_metric_row("CO", "Bogota", "Z1", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Bogota", "Z2", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Medellin", "Z3", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
            _make_metric_row("CO", "Cali", "Z4", "Perfect Orders", l0w=0.5, l1w=0.5, l2w=0.5, l3w=0.5),
        ]
        db = _create_db(rows)
        svc = InsightsService(db)
        report = svc.generate_report()
        assert isinstance(report, InsightReport)
        assert all(v == 0 for v in report.category_counts.values())
