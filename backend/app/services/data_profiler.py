"""Dynamic Data Profiler — queries DuckDB at startup to build real-time business context."""

from __future__ import annotations

import logging
from typing import Any

from app.core.database import DuckDBService

logger = logging.getLogger(__name__)

# Key metrics to profile (subset for conciseness)
_KEY_METRICS = [
    "Perfect Orders",
    "Gross Profit UE",
    "Lead Penetration",
    "Pro Adoption",
    "Turbo Adoption",
]


class DataProfiler:
    """Generates a concise data profile from DuckDB for injection into the LLM system prompt."""

    def __init__(self, db: DuckDBService) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_profile(self) -> str:
        """Return a markdown string with the full data profile (runs all profiling queries)."""
        sections: list[str] = []
        sections.append("## Current Data Profile (auto-generated from data)\n")

        sections.append(self._metric_averages_by_country())
        sections.append(self._trends_vs_4w())
        sections.append(self._zones_requiring_attention())
        sections.append(self._top_performing_zones())
        sections.append(self._order_volume_context())
        sections.append(self._data_glossary())

        return "\n".join(s for s in sections if s)

    # ------------------------------------------------------------------
    # Private profiling methods
    # ------------------------------------------------------------------

    def _metric_averages_by_country(self) -> str:
        """Per-metric AVG(L0W_ROLL) grouped by COUNTRY for key metrics."""
        try:
            metrics_list = ", ".join(f"'{m}'" for m in _KEY_METRICS)
            rows = self.db.execute(f"""
                SELECT COUNTRY, METRIC, ROUND(AVG(L0W_ROLL), 4) AS avg_val
                FROM raw_input_metrics
                WHERE METRIC IN ({metrics_list})
                GROUP BY COUNTRY, METRIC
                ORDER BY COUNTRY, METRIC
            """)
            if not rows:
                return ""

            # Pivot: {country: {metric: val}}
            pivot: dict[str, dict[str, float]] = {}
            for r in rows:
                pivot.setdefault(r["COUNTRY"], {})[r["METRIC"]] = r["avg_val"]

            countries = sorted(pivot.keys())
            header_metrics = [m for m in _KEY_METRICS if any(m in pivot[c] for c in countries)]

            lines = ["### Metric Averages by Country (This Week - L0W)"]
            header = "| Country | " + " | ".join(header_metrics) + " |"
            sep = "|" + "|".join(["---"] * (len(header_metrics) + 1)) + "|"
            lines.append(header)
            lines.append(sep)

            for c in countries:
                vals = []
                for m in header_metrics:
                    v = pivot[c].get(m)
                    vals.append(_fmt_metric(v, m))
                lines.append(f"| {c} | " + " | ".join(vals) + " |")

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: metric averages failed: %s", e)
            return ""

    def _trends_vs_4w(self) -> str:
        """Compare AVG(L0W_ROLL) vs AVG(L4W_ROLL) per metric globally."""
        try:
            metrics_list = ", ".join(f"'{m}'" for m in _KEY_METRICS)
            rows = self.db.execute(f"""
                SELECT METRIC,
                       ROUND(AVG(L0W_ROLL), 4) AS avg_now,
                       ROUND(AVG(L4W_ROLL), 4) AS avg_4w
                FROM raw_input_metrics
                WHERE METRIC IN ({metrics_list})
                GROUP BY METRIC
                ORDER BY METRIC
            """)
            if not rows:
                return ""

            lines = ["### Trends vs 4 Weeks Ago"]
            for r in rows:
                now, ago = r["avg_now"], r["avg_4w"]
                if now is None or ago is None:
                    continue
                diff = now - ago
                direction = "improving" if diff > 0 else "declining" if diff < 0 else "flat"
                sign = "+" if diff >= 0 else ""
                lines.append(f"- {r['METRIC']}: {sign}{diff:.4f} ({direction})")

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: trends failed: %s", e)
            return ""

    def _zones_requiring_attention(self) -> str:
        """Top 5 zones with biggest decline (L0W_ROLL - L4W_ROLL) for key metrics."""
        try:
            metrics_list = ", ".join(f"'{m}'" for m in _KEY_METRICS)
            rows = self.db.execute(f"""
                SELECT DISTINCT ZONE, CITY, COUNTRY, METRIC,
                       ROUND(L0W_ROLL, 4) AS current_val,
                       ROUND(L4W_ROLL, 4) AS val_4w,
                       ROUND(L0W_ROLL - L4W_ROLL, 4) AS change
                FROM raw_input_metrics
                WHERE METRIC IN ({metrics_list})
                  AND L0W_ROLL IS NOT NULL AND L4W_ROLL IS NOT NULL
                ORDER BY change ASC
                LIMIT 5
            """)
            if not rows:
                return ""

            lines = ["### Zones Requiring Attention (biggest declines L0W vs L4W)"]
            lines.append("| Zone | City | Country | Metric | Current | 4W Ago | Change |")
            lines.append("|------|------|---------|--------|---------|--------|--------|")
            for r in rows:
                m = r["METRIC"]
                lines.append(
                    f"| {r['ZONE']} | {r['CITY']} | {r['COUNTRY']} | {m} "
                    f"| {_fmt_metric(r['current_val'], m)} "
                    f"| {_fmt_metric(r['val_4w'], m)} "
                    f"| {r['change']:+.4f} |"
                )

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: zones attention failed: %s", e)
            return ""

    def _top_performing_zones(self) -> str:
        """Top 5 zones by L0W_ROLL for Perfect Orders (normalized 0-1 metric)."""
        try:
            rows = self.db.execute("""
                SELECT DISTINCT ZONE, CITY, COUNTRY, METRIC, ROUND(L0W_ROLL, 4) AS current_val
                FROM raw_input_metrics
                WHERE METRIC = 'Perfect Orders'
                  AND L0W_ROLL IS NOT NULL
                ORDER BY L0W_ROLL DESC
                LIMIT 5
            """)
            if not rows:
                return ""

            lines = ["### Top Performing Zones"]
            lines.append("| Zone | City | Country | Metric | Current |")
            lines.append("|------|------|---------|--------|---------|")
            for r in rows:
                m = r["METRIC"]
                lines.append(
                    f"| {r['ZONE']} | {r['CITY']} | {r['COUNTRY']} | {m} "
                    f"| {_fmt_metric(r['current_val'], m)} |"
                )

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: top zones failed: %s", e)
            return ""

    def _order_volume_context(self) -> str:
        """Total orders this week (L0W) by country + trend vs 4 weeks ago."""
        try:
            rows = self.db.execute("""
                SELECT COUNTRY,
                       SUM(L0W) AS orders_now,
                       SUM(L4W) AS orders_4w
                FROM raw_orders
                GROUP BY COUNTRY
                ORDER BY orders_now DESC
            """)
            if not rows:
                return ""

            lines = ["### Order Volume by Country (This Week)"]
            lines.append("| Country | Orders (L0W) | Orders (L4W) | Change |")
            lines.append("|---------|-------------|-------------|--------|")
            for r in rows:
                now = r["orders_now"] or 0
                ago = r["orders_4w"] or 0
                diff = now - ago
                pct = (diff / ago * 100) if ago else 0
                sign = "+" if diff >= 0 else ""
                lines.append(
                    f"| {r['COUNTRY']} | {now:,.0f} | {ago:,.0f} | {sign}{pct:.1f}% |"
                )

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: order volume failed: %s", e)
            return ""

    def _data_glossary(self) -> str:
        """Load raw_summary table and format as a data glossary."""
        try:
            rows = self.db.execute("SELECT * FROM raw_summary LIMIT 100")
            if not rows:
                return ""

            # Detect column names (may vary slightly)
            cols = list(rows[0].keys())
            lines = ["### Data Glossary (from RAW_SUMMARY)"]
            header = "| " + " | ".join(cols) + " |"
            sep = "|" + "|".join(["---"] * len(cols)) + "|"
            lines.append(header)
            lines.append(sep)
            for r in rows:
                vals = [str(r.get(c, "")).replace("|", "/") for c in cols]
                lines.append("| " + " | ".join(vals) + " |")

            return "\n".join(lines) + "\n"
        except Exception as e:
            logger.warning("DataProfiler: glossary failed: %s", e)
            return ""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _fmt_metric(val: Any, metric_name: str) -> str:
    """Format a metric value based on the metric type."""
    if val is None:
        return "N/A"
    if "Orders" in metric_name or "Adoption" in metric_name or "Penetration" in metric_name:
        return f"{val * 100:.1f}%" if abs(val) < 10 else f"{val:.2f}"
    if "Profit" in metric_name:
        return f"${val:.2f}"
    return f"{val:.2f}"
