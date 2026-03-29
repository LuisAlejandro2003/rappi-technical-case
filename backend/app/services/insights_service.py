"""Automatic Insights Service — detects anomalies, trends, benchmarking gaps,
correlations, and opportunities from operational data in DuckDB."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader

from app.core.database import DuckDBService
from app.models.schemas import Insight, InsightReport
from app.services.insights_config import (
    ANOMALY_THRESHOLD,
    BENCHMARK_DIVERGENCE_THRESHOLD,
    BENCHMARK_MIN_PEER_GROUP,
    CATEGORY_WEIGHTS,
    CORRELATED_PAIRS,
    DEFAULT_POLARITY,
    MAX_FINDINGS_PER_CATEGORY,
    MAX_FINDINGS_PER_DETECTOR,
    MAX_FINDINGS_PER_METRIC_PER_CATEGORY,
    MAX_TOTAL_FINDINGS,
    METRIC_DISPLAY_TYPE,
    METRIC_POLARITY,
    OPPORTUNITY_BELOW_THRESHOLD,
    OPPORTUNITY_MAX_WEAK_METRICS,
    OPPORTUNITY_MIN_MAGNITUDE,
    SEVERITY_MAGNITUDE_CAP,
    TREND_MIN_MAGNITUDE,
    TREND_MIN_WEEKS,
)

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    keep_trailing_newline=True,
)

# Protocol for LLM to avoid circular imports
from typing import Protocol


class _LLMGenerateProtocol(Protocol):
    def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> object: ...


class InsightsService:
    """Runs five insight detectors against DuckDB and produces a ranked report."""

    def __init__(self, db: DuckDBService, llm: _LLMGenerateProtocol | None = None) -> None:
        self.db = db
        self.llm = llm
        self._cached_report: InsightReport | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(self) -> InsightReport:
        """Run all 5 detectors, score, rank, build report."""
        findings: list[Insight] = []
        findings.extend(self.detect_anomalies())
        findings.extend(self.detect_trends())
        findings.extend(self.detect_benchmarking())
        findings.extend(self.detect_correlations())
        findings.extend(self.detect_opportunities())

        # Cap magnitude to prevent outliers from dominating
        for f in findings:
            if abs(f.magnitude) > SEVERITY_MAGNITUDE_CAP:
                f.magnitude = SEVERITY_MAGNITUDE_CAP if f.magnitude > 0 else -SEVERITY_MAGNITUDE_CAP
                f.severity = SEVERITY_MAGNITUDE_CAP * CATEGORY_WEIGHTS.get(f.category, 1.0)

        # Deduplicate: same zone + metric = keep highest severity only
        seen: set[tuple[str, str, str]] = set()
        deduped: list[Insight] = []
        for f in findings:
            key = (f.zone or "", f.metrics[0] if f.metrics else "", f.category)
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        findings = deduped

        # Limit per category with metric diversity
        capped: list[Insight] = []
        for cat in CATEGORY_WEIGHTS:
            cat_findings = sorted(
                [f for f in findings if f.category == cat],
                key=lambda f: f.severity,
                reverse=True,
            )
            # Enforce metric diversity: max N findings per metric within category
            metric_counts: dict[str, int] = {}
            selected: list[Insight] = []
            for f in cat_findings:
                metric_key = f.metrics[0] if f.metrics else ""
                count = metric_counts.get(metric_key, 0)
                if count >= MAX_FINDINGS_PER_METRIC_PER_CATEGORY:
                    continue
                metric_counts[metric_key] = count + 1
                selected.append(f)
                if len(selected) >= MAX_FINDINGS_PER_CATEGORY:
                    break
            capped.extend(selected)

        # Sort by severity descending, cap total
        capped.sort(key=lambda f: f.severity, reverse=True)
        findings = capped[:MAX_TOTAL_FINDINGS]

        report = InsightReport(
            id=f"report_{uuid4().hex[:8]}",
            findings=findings,
            category_counts={
                cat: sum(1 for f in findings if f.category == cat)
                for cat in CATEGORY_WEIGHTS
            },
        )
        self._cached_report = report
        return report

    def get_cached_report(self) -> InsightReport | None:
        return self._cached_report

    def generate_narrative(self, report: InsightReport) -> str:
        """Use LLM to generate a markdown executive report from structured findings."""
        if not self.llm:
            logger.warning("No LLM provider — returning empty narrative")
            return ""

        top_findings = report.findings[:5]
        findings_by_category: dict[str, list[Insight]] = {}
        for cat in CATEGORY_WEIGHTS:
            items = [f for f in report.findings if f.category == cat]
            if items:
                findings_by_category[cat] = items[:10]  # cap per category

        template = _jinja_env.get_template("insights_prompt.j2")
        prompt_text = template.render(
            total_findings=len(report.findings),
            category_counts=report.category_counts,
            top_findings=top_findings,
            findings_by_category=findings_by_category,
        )

        try:
            response = self.llm.generate(
                system_prompt=prompt_text,
                messages=[{"role": "user", "content": "Genera el reporte ejecutivo de insights."}],
                tools=None,
            )
            return response.content or ""
        except Exception as e:
            logger.error("LLM narrative generation failed: %s", e)
            return ""

    def build_insights_summary(self) -> str:
        """Build a concise summary of latest insights for injection into chat system prompt."""
        report = self._cached_report
        if not report or not report.findings:
            return ""

        lines = ["## Ultimos Insights Detectados (resumen automatico)"]
        for f in report.findings[:5]:
            lines.append(f"- **[{f.category.upper()}]** {f.title}")
        lines.append(
            f"\nTotal: {len(report.findings)} hallazgos en {sum(1 for c in report.category_counts.values() if c > 0)} categorias."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Detector 1: Anomalies (week-over-week spikes / drops)
    # ------------------------------------------------------------------

    def detect_anomalies(self) -> list[Insight]:
        """Compare L0W_ROLL vs L1W_ROLL per ZONE/METRIC — flag large WoW changes."""
        try:
            rows = self.db.execute(f"""
                SELECT
                    ZONE, CITY, COUNTRY, METRIC,
                    L0W_ROLL, L1W_ROLL,
                    CASE
                        WHEN ABS(L1W_ROLL) = 0 AND L0W_ROLL != 0 THEN 1.0
                        WHEN ABS(L1W_ROLL) = 0 THEN 0.0
                        ELSE (L0W_ROLL - L1W_ROLL) / ABS(L1W_ROLL)
                    END AS magnitude
                FROM raw_input_metrics
                WHERE L0W_ROLL IS NOT NULL
                  AND L1W_ROLL IS NOT NULL
                  AND (
                      ABS(L1W_ROLL) = 0 AND L0W_ROLL != 0
                      OR ABS((L0W_ROLL - L1W_ROLL) / NULLIF(ABS(L1W_ROLL), 0)) > {ANOMALY_THRESHOLD}
                  )
                ORDER BY ABS(magnitude) DESC
                LIMIT 100
            """)

            findings: list[Insight] = []
            for r in rows:
                if len(findings) >= MAX_FINDINGS_PER_DETECTOR:
                    break
                metric = r["METRIC"]
                mag = float(r["magnitude"])
                direction = self._classify_direction(metric, mag)
                severity = abs(mag) * CATEGORY_WEIGHTS["anomalias"]
                change_desc = self._fmt_change(metric, float(r['L1W_ROLL']), float(r['L0W_ROLL']))
                dir_label = "mejora" if direction == "improvement" else "deterioro"
                insight = Insight(
                    id=f"anomalias_{uuid4().hex[:8]}",
                    category="anomalias",
                    severity=round(severity, 4),
                    title=f"{dir_label.capitalize()} significativo en {metric} en {r['ZONE']} ({r['COUNTRY']})",
                    description=(
                        f"{metric} pasó {change_desc} en una semana."
                    ),
                    zone=r["ZONE"],
                    city=r["CITY"],
                    country=r["COUNTRY"],
                    metrics=[metric],
                    magnitude=round(mag, 4),
                    direction=direction,
                    explore_query=self._build_explore_query(
                        "anomalias",
                        zone=r["ZONE"],
                        country=r["COUNTRY"],
                        metric=metric,
                        magnitude=mag * 100,
                    ),
                )
                findings.append(insight)
            return findings

        except Exception as e:
            logger.error("detect_anomalies failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Detector 2: Trends (3+ consecutive declining weeks)
    # ------------------------------------------------------------------

    def detect_trends(self) -> list[Insight]:
        """Check for 3–5 consecutive declining weeks per ZONE/METRIC."""
        try:
            findings: list[Insight] = []

            # Check 5-week, 4-week, and 3-week trends (longest first)
            for n_weeks in (5, 4, 3):
                week_cols = [f"L{i}W_ROLL" for i in range(n_weeks)]  # L0W..L(n-1)W
                null_checks = " AND ".join(f"{c} IS NOT NULL" for c in week_cols)

                # Build decline conditions for higher_is_better metrics
                # (each week < previous week = declining)
                hib_conditions = " AND ".join(
                    f"L{i}W_ROLL < L{i+1}W_ROLL" for i in range(n_weeks - 1)
                )
                # For lower_is_better (increasing is bad)
                lib_conditions = " AND ".join(
                    f"L{i}W_ROLL > L{i+1}W_ROLL" for i in range(n_weeks - 1)
                )

                last_col = f"L{n_weeks - 1}W_ROLL"

                rows = self.db.execute(f"""
                    SELECT ZONE, CITY, COUNTRY, METRIC,
                           L0W_ROLL, {last_col} AS baseline,
                           CASE
                               WHEN ABS({last_col}) = 0 THEN 1.0
                               ELSE ABS(L0W_ROLL - {last_col}) / ABS({last_col})
                           END AS magnitude,
                           {n_weeks} AS n_weeks
                    FROM raw_input_metrics
                    WHERE {null_checks}
                      AND (
                          ({hib_conditions})
                          OR ({lib_conditions})
                      )
                      AND CASE
                              WHEN ABS({last_col}) = 0 THEN 1.0
                              ELSE ABS(L0W_ROLL - {last_col}) / ABS({last_col})
                          END > {TREND_MIN_MAGNITUDE}
                    ORDER BY magnitude DESC
                    LIMIT 100
                """)

                for r in rows:
                    if len(findings) >= MAX_FINDINGS_PER_DETECTOR:
                        break
                    metric = r["METRIC"]
                    polarity = self._get_polarity(metric)
                    l0 = float(r["L0W_ROLL"])
                    baseline = float(r["baseline"])
                    change = l0 - baseline

                    # Determine if this is actually a deterioration
                    if polarity == "higher_is_better" and change >= 0:
                        continue  # improving, not a trend problem
                    if polarity == "lower_is_better" and change <= 0:
                        continue  # improving (decreasing)

                    mag = float(r["magnitude"])
                    severity = mag * CATEGORY_WEIGHTS["tendencias"]
                    # Longer trends get a boost
                    severity *= 1 + (n_weeks - TREND_MIN_WEEKS) * 0.15

                    zone_key = (r["ZONE"], metric)
                    # Skip if already found with longer trend
                    if any(
                        f.zone == r["ZONE"] and metric in f.metrics
                        for f in findings
                    ):
                        continue

                    change_desc = self._fmt_change(metric, baseline, l0)
                    findings.append(Insight(
                        id=f"tendencias_{uuid4().hex[:8]}",
                        category="tendencias",
                        severity=round(severity, 4),
                        title=f"{metric} lleva {n_weeks} semanas de deterioro en {r['ZONE']} ({r['COUNTRY']})",
                        description=(
                            f"{metric} pasó {change_desc} en {n_weeks} semanas consecutivas."
                        ),
                        zone=r["ZONE"],
                        city=r["CITY"],
                        country=r["COUNTRY"],
                        metrics=[metric],
                        magnitude=round(mag, 4),
                        direction="deterioration",
                        explore_query=self._build_explore_query(
                            "tendencias",
                            zone=r["ZONE"],
                            country=r["COUNTRY"],
                            metric=metric,
                            n_weeks=n_weeks,
                        ),
                    ))

            return findings

        except Exception as e:
            logger.error("detect_trends failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Detector 3: Benchmarking (divergence from peer median)
    # ------------------------------------------------------------------

    def detect_benchmarking(self) -> list[Insight]:
        """Find zones significantly diverging from their country peer median."""
        try:
            rows = self.db.execute(f"""
                WITH peer_medians AS (
                    SELECT COUNTRY, METRIC,
                           MEDIAN(L0W_ROLL) AS peer_median,
                           COUNT(*) AS peer_count
                    FROM raw_input_metrics
                    WHERE L0W_ROLL IS NOT NULL
                    GROUP BY COUNTRY, METRIC
                    HAVING COUNT(*) >= {BENCHMARK_MIN_PEER_GROUP}
                )
                SELECT m.ZONE, m.CITY, m.COUNTRY, m.METRIC,
                       m.L0W_ROLL AS zone_val,
                       p.peer_median,
                       CASE
                           WHEN ABS(p.peer_median) = 0 THEN 0.0
                           ELSE (m.L0W_ROLL - p.peer_median) / ABS(p.peer_median)
                       END AS divergence
                FROM raw_input_metrics m
                JOIN peer_medians p
                  ON m.COUNTRY = p.COUNTRY AND m.METRIC = p.METRIC
                WHERE m.L0W_ROLL IS NOT NULL
                  AND ABS(CASE
                          WHEN ABS(p.peer_median) = 0 THEN 0.0
                          ELSE (m.L0W_ROLL - p.peer_median) / ABS(p.peer_median)
                      END) > {BENCHMARK_DIVERGENCE_THRESHOLD}
                ORDER BY ABS(divergence) DESC
                LIMIT 100
            """)

            findings: list[Insight] = []
            for r in rows:
                if len(findings) >= MAX_FINDINGS_PER_DETECTOR:
                    break
                metric = r["METRIC"]
                polarity = self._get_polarity(metric)
                divergence = float(r["divergence"])

                # Only flag underperformers relative to polarity
                if polarity == "higher_is_better" and divergence >= 0:
                    continue  # above median is good
                if polarity == "lower_is_better" and divergence <= 0:
                    continue  # below median is good

                severity = abs(divergence) * CATEGORY_WEIGHTS["benchmarking"]
                div_desc = self._fmt_divergence(metric, float(r['zone_val']), float(r['peer_median']))
                findings.append(Insight(
                    id=f"benchmarking_{uuid4().hex[:8]}",
                    category="benchmarking",
                    severity=round(severity, 4),
                    title=f"{r['ZONE']} ({r['COUNTRY']}) por {'debajo' if divergence < 0 else 'encima'} del promedio en {metric}",
                    description=(
                        f"{metric}: {div_desc}."
                    ),
                    zone=r["ZONE"],
                    city=r["CITY"],
                    country=r["COUNTRY"],
                    metrics=[metric],
                    magnitude=round(abs(divergence), 4),
                    direction="deterioration",
                    explore_query=self._build_explore_query(
                        "benchmarking",
                        zone=r["ZONE"],
                        country=r["COUNTRY"],
                        metric=metric,
                        divergence=divergence * 100,
                    ),
                ))

            return findings

        except Exception as e:
            logger.error("detect_benchmarking failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Detector 4: Correlations (paired metric under-performance)
    # ------------------------------------------------------------------

    def detect_correlations(self) -> list[Insight]:
        """For each correlated pair, find zones where both metrics are below/above median."""
        try:
            findings: list[Insight] = []

            for metric_a, metric_b, inverse in CORRELATED_PAIRS:
                rows = self.db.execute(f"""
                    WITH medians AS (
                        SELECT COUNTRY, METRIC,
                               MEDIAN(L0W_ROLL) AS med
                        FROM raw_input_metrics
                        WHERE METRIC IN ('{metric_a}', '{metric_b}')
                          AND L0W_ROLL IS NOT NULL
                        GROUP BY COUNTRY, METRIC
                    ),
                    zone_vals AS (
                        SELECT m.ZONE, m.CITY, m.COUNTRY, m.METRIC, m.L0W_ROLL,
                               med.med AS peer_median,
                               CASE
                                   WHEN ABS(med.med) = 0 THEN 0.0
                                   ELSE (m.L0W_ROLL - med.med) / ABS(med.med)
                               END AS deviation
                        FROM raw_input_metrics m
                        JOIN medians med
                          ON m.COUNTRY = med.COUNTRY AND m.METRIC = med.METRIC
                        WHERE m.L0W_ROLL IS NOT NULL
                    ),
                    paired AS (
                        SELECT a.ZONE, a.CITY, a.COUNTRY,
                               a.deviation AS dev_a,
                               b.deviation AS dev_b
                        FROM zone_vals a
                        JOIN zone_vals b
                          ON a.ZONE = b.ZONE AND a.COUNTRY = b.COUNTRY
                        WHERE a.METRIC = '{metric_a}'
                          AND b.METRIC = '{metric_b}'
                    )
                    SELECT ZONE, CITY, COUNTRY, dev_a, dev_b
                    FROM paired
                    WHERE {'dev_a < 0 AND dev_b > 0' if inverse else 'dev_a < 0 AND dev_b < 0'}
                    ORDER BY ABS(dev_a) + ABS(dev_b) DESC
                    LIMIT 50
                """)

                for r in rows:
                    dev_a = float(r["dev_a"])
                    dev_b = float(r["dev_b"])
                    mag = (abs(dev_a) + abs(dev_b)) / 2.0
                    severity = mag * CATEGORY_WEIGHTS["correlaciones"]

                    if inverse:
                        desc_relation = f"{metric_a} por debajo y {metric_b} por encima"
                    else:
                        desc_relation = f"tanto {metric_a} como {metric_b} por debajo"

                    # Format deviations: show relative % below median
                    fmt_a = f"{abs(dev_a):.0%}"
                    fmt_b = f"{abs(dev_b):.0%}"

                    findings.append(Insight(
                        id=f"correlaciones_{uuid4().hex[:8]}",
                        category="correlaciones",
                        severity=round(severity, 4),
                        title=f"{r['ZONE']} ({r['COUNTRY']}): {desc_relation} del promedio",
                        description=(
                            f"{metric_a} está {fmt_a} por debajo de la mediana "
                            f"y {metric_b} está {fmt_b} por debajo. "
                            f"Ambas métricas débiles sugieren un problema estructural."
                        ),
                        zone=r["ZONE"],
                        city=r["CITY"],
                        country=r["COUNTRY"],
                        metrics=[metric_a, metric_b],
                        magnitude=round(mag, 4),
                        direction="deterioration",
                        explore_query=self._build_explore_query(
                            "correlaciones",
                            zone=r["ZONE"],
                            country=r["COUNTRY"],
                            metric_a=metric_a,
                            metric_b=metric_b,
                        ),
                    ))

            return findings

        except Exception as e:
            logger.error("detect_correlations failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Detector 5: Opportunities (improving trends + targeted weaknesses)
    # ------------------------------------------------------------------

    def detect_opportunities(self) -> list[Insight]:
        """Detect improving trends and zones with only 1-2 weak metrics."""
        try:
            findings: list[Insight] = []
            findings.extend(self._detect_improving_trends())
            findings.extend(self._detect_targeted_weaknesses())
            return findings
        except Exception as e:
            logger.error("detect_opportunities failed: %s", e)
            return []

    def _detect_improving_trends(self) -> list[Insight]:
        """Inverse of detect_trends: 3+ consecutive improving weeks."""
        findings: list[Insight] = []

        for n_weeks in (5, 4, 3):
            week_cols = [f"L{i}W_ROLL" for i in range(n_weeks)]
            null_checks = " AND ".join(f"{c} IS NOT NULL" for c in week_cols)

            # Improving for higher_is_better: L0W > L1W > L2W > ...
            hib_conditions = " AND ".join(
                f"L{i}W_ROLL > L{i+1}W_ROLL" for i in range(n_weeks - 1)
            )
            # Improving for lower_is_better: L0W < L1W < L2W < ...
            lib_conditions = " AND ".join(
                f"L{i}W_ROLL < L{i+1}W_ROLL" for i in range(n_weeks - 1)
            )

            last_col = f"L{n_weeks - 1}W_ROLL"

            rows = self.db.execute(f"""
                SELECT ZONE, CITY, COUNTRY, METRIC,
                       L0W_ROLL, {last_col} AS baseline,
                       CASE
                           WHEN ABS({last_col}) = 0 THEN 1.0
                           ELSE ABS(L0W_ROLL - {last_col}) / ABS({last_col})
                       END AS magnitude,
                       {n_weeks} AS n_weeks
                FROM raw_input_metrics
                WHERE {null_checks}
                  AND (
                      ({hib_conditions})
                      OR ({lib_conditions})
                  )
                  AND CASE
                          WHEN ABS({last_col}) = 0 THEN 1.0
                          ELSE ABS(L0W_ROLL - {last_col}) / ABS({last_col})
                      END > {OPPORTUNITY_MIN_MAGNITUDE}
                ORDER BY magnitude DESC
                LIMIT 100
            """)

            for r in rows:
                if len(findings) >= MAX_FINDINGS_PER_DETECTOR:
                    break
                metric = r["METRIC"]
                polarity = self._get_polarity(metric)
                l0 = float(r["L0W_ROLL"])
                baseline = float(r["baseline"])
                change = l0 - baseline

                # Only keep actual improvements
                if polarity == "higher_is_better" and change <= 0:
                    continue
                if polarity == "lower_is_better" and change >= 0:
                    continue

                # Skip if already found with longer trend
                if any(
                    f.zone == r["ZONE"] and metric in f.metrics
                    for f in findings
                ):
                    continue

                mag = float(r["magnitude"])
                severity = mag * CATEGORY_WEIGHTS["oportunidades"]
                severity *= 1 + (n_weeks - TREND_MIN_WEEKS) * 0.15

                change_desc = self._fmt_change(metric, baseline, l0)
                findings.append(Insight(
                    id=f"oportunidades_{uuid4().hex[:8]}",
                    category="oportunidades",
                    severity=round(severity, 4),
                    title=f"{metric} mejora {n_weeks} semanas seguidas en {r['ZONE']} ({r['COUNTRY']})",
                    description=(
                        f"{metric} mejoró {change_desc} en {n_weeks} semanas consecutivas."
                    ),
                    zone=r["ZONE"],
                    city=r["CITY"],
                    country=r["COUNTRY"],
                    metrics=[metric],
                    magnitude=round(mag, 4),
                    direction="improvement",
                    explore_query=self._build_explore_query(
                        "oportunidades",
                        zone=r["ZONE"],
                        country=r["COUNTRY"],
                        metric=metric,
                    ),
                ))

        return findings

    def _detect_targeted_weaknesses(self) -> list[Insight]:
        """Zones with only 1-2 metrics significantly below peer median."""
        findings: list[Insight] = []

        rows = self.db.execute(f"""
            WITH peer_medians AS (
                SELECT COUNTRY, METRIC,
                       MEDIAN(L0W_ROLL) AS peer_median
                FROM raw_input_metrics
                WHERE L0W_ROLL IS NOT NULL
                GROUP BY COUNTRY, METRIC
                HAVING COUNT(*) >= {BENCHMARK_MIN_PEER_GROUP}
            ),
            deviations AS (
                SELECT m.ZONE, m.CITY, m.COUNTRY, m.METRIC,
                       m.L0W_ROLL,
                       p.peer_median,
                       CASE
                           WHEN ABS(p.peer_median) = 0 THEN 0.0
                           ELSE (m.L0W_ROLL - p.peer_median) / ABS(p.peer_median)
                       END AS deviation
                FROM raw_input_metrics m
                JOIN peer_medians p
                  ON m.COUNTRY = p.COUNTRY AND m.METRIC = p.METRIC
                WHERE m.L0W_ROLL IS NOT NULL
            ),
            weak_counts AS (
                SELECT ZONE, COUNTRY, CITY,
                       COUNT(*) AS weak_metric_count,
                       LIST(METRIC) AS weak_metrics,
                       AVG(ABS(deviation)) AS avg_deviation
                FROM deviations
                WHERE deviation < -{OPPORTUNITY_BELOW_THRESHOLD}
                GROUP BY ZONE, COUNTRY, CITY
                HAVING COUNT(*) BETWEEN 1 AND {OPPORTUNITY_MAX_WEAK_METRICS}
            )
            SELECT * FROM weak_counts
            ORDER BY avg_deviation DESC
            LIMIT 50
        """)

        for r in rows:
            weak_metrics = r["weak_metrics"]
            if isinstance(weak_metrics, str):
                weak_metrics = [weak_metrics]
            mag = float(r["avg_deviation"])
            severity = mag * CATEGORY_WEIGHTS["oportunidades"]

            findings.append(Insight(
                id=f"oportunidades_{uuid4().hex[:8]}",
                category="oportunidades",
                severity=round(severity, 4),
                title=f"{r['ZONE']} tiene solo {r['weak_metric_count']} métricas débiles — oportunidad focalizada",
                description=(
                    f"{r['ZONE']} ({r['COUNTRY']}): {', '.join(str(m) for m in weak_metrics)} "
                    f"están significativamente por debajo de la mediana de pares "
                    f"(desviación promedio {mag:.1%}). "
                    f"Intervención focalizada posible."
                ),
                zone=r["ZONE"],
                city=r["CITY"],
                country=r["COUNTRY"],
                metrics=[str(m) for m in weak_metrics],
                magnitude=round(mag, 4),
                direction="neutral",
                explore_query=self._build_explore_query(
                    "oportunidades_debilidad",
                    zone=r["ZONE"],
                    country=r["COUNTRY"],
                    metric=", ".join(str(m) for m in weak_metrics),
                ),
            ))

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_narrative_sections(markdown: str) -> dict[str, str]:
        """Parse LLM-generated markdown into sections keyed by category.

        Looks for ### headings and maps them to category keys:
          "Resumen Ejecutivo" → "resumen"
          "Anomalias Detectadas" → "anomalias"
          "Tendencias Preocupantes" → "tendencias"
          "Benchmarking entre Zonas" → "benchmarking"
          "Correlaciones Identificadas" → "correlaciones"
          "Oportunidades" → "oportunidades"
        """
        if not markdown:
            return {}

        heading_map = {
            "resumen ejecutivo": "resumen",
            "resumen": "resumen",
            "anomalias detectadas": "anomalias",
            "anomalías detectadas": "anomalias",
            "anomalias": "anomalias",
            "anomalías": "anomalias",
            "tendencias preocupantes": "tendencias",
            "tendencias": "tendencias",
            "benchmarking entre zonas": "benchmarking",
            "benchmarking": "benchmarking",
            "correlaciones identificadas": "correlaciones",
            "correlaciones": "correlaciones",
            "oportunidades": "oportunidades",
        }

        sections: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in markdown.split("\n"):
            stripped = line.strip()

            # Detect any markdown heading (# through ####)
            if not stripped.startswith("#"):
                if current_key is not None:
                    current_lines.append(line)
                continue

            heading_text = stripped.lstrip("#").strip().lower()

            # Try to match against known section headings
            matched_key: str | None = None
            for pattern, key in heading_map.items():
                if pattern in heading_text:
                    matched_key = key
                    break

            if matched_key is not None:
                # This is a recognized section heading — start new section
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = matched_key
                current_lines = []
            else:
                # Unrecognized heading — treat as content within current section
                if current_key is not None:
                    current_lines.append(line)

        # Save last section
        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

        return sections

    @staticmethod
    def _get_polarity(metric: str) -> str:
        return METRIC_POLARITY.get(metric, DEFAULT_POLARITY)

    @staticmethod
    def _classify_direction(metric: str, change_value: float) -> str:
        polarity = METRIC_POLARITY.get(metric, DEFAULT_POLARITY)
        if polarity == "higher_is_better":
            return "improvement" if change_value > 0 else "deterioration"
        else:  # lower_is_better
            return "improvement" if change_value < 0 else "deterioration"

    @staticmethod
    def _fmt_value(metric: str, value: float) -> str:
        """Format a metric value for human display."""
        display_type = METRIC_DISPLAY_TYPE.get(metric, "ratio")
        if display_type == "dollar":
            # Use 4 decimals for tiny values to avoid showing $0.00
            if 0 < abs(value) < 0.01:
                return f"${value:.4f}"
            return f"${value:.2f}"
        else:  # ratio: 0-1 → show as percentage
            return f"{value * 100:.1f}%"

    @staticmethod
    def _fmt_change(metric: str, old_val: float, new_val: float) -> str:
        """Describe a change in human-readable terms."""
        display_type = METRIC_DISPLAY_TYPE.get(metric, "ratio")
        if display_type == "dollar":
            diff = new_val - old_val
            return f"de {InsightsService._fmt_value(metric, old_val)} a {InsightsService._fmt_value(metric, new_val)} ({'+' if diff > 0 else ''}{InsightsService._fmt_value(metric, diff)})"
        else:
            diff_pp = (new_val - old_val) * 100
            return f"de {InsightsService._fmt_value(metric, old_val)} a {InsightsService._fmt_value(metric, new_val)} ({'+' if diff_pp > 0 else ''}{diff_pp:.1f}pp)"

    @staticmethod
    def _fmt_divergence(metric: str, zone_val: float, median_val: float) -> str:
        """Describe divergence from median in human terms."""
        display_type = METRIC_DISPLAY_TYPE.get(metric, "ratio")
        if display_type == "dollar":
            gap = abs(zone_val - median_val)
            return f"{InsightsService._fmt_value(metric, zone_val)} vs mediana {InsightsService._fmt_value(metric, median_val)} (brecha de ${gap:.2f})"
        else:
            gap_pp = abs(zone_val - median_val) * 100
            return f"{InsightsService._fmt_value(metric, zone_val)} vs mediana {InsightsService._fmt_value(metric, median_val)} ({gap_pp:.1f}pp de brecha)"

    @staticmethod
    def _build_explore_query(category: str, **kwargs) -> str:
        templates = {
            "anomalias": (
                "Analiza por qué {zone} ({country}) tuvo un cambio de "
                "{magnitude:.1f}% en {metric} esta semana. "
                "Qué factores podrían explicarlo?"
            ),
            "tendencias": (
                "La zona {zone} ha tenido {n_weeks} semanas consecutivas "
                "de deterioro en {metric}. Muestra la evolución y posibles causas."
            ),
            "benchmarking": (
                "Compara {zone} con otras zonas de {country} en {metric}. "
                "Está {divergence:.0f}% por debajo del promedio."
            ),
            "correlaciones": (
                "En {zone} ({country}), tanto {metric_a} como {metric_b} "
                "están por debajo del promedio. Analiza la relación."
            ),
            "oportunidades": (
                "La zona {zone} está mejorando en {metric}. "
                "Analiza qué está impulsando esta mejora."
            ),
            "oportunidades_debilidad": (
                "La zona {zone} ({country}) tiene debilidades focalizadas "
                "en {metric}. Sugiere intervenciones específicas."
            ),
        }
        template = templates.get(category, "Analiza {zone} en detalle.")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
