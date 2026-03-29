import json
import logging

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_insights_service
from app.services.insights_service import InsightsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights")


@router.post("/generate")
async def generate_insights(
    service: InsightsService = Depends(get_insights_service),
):
    """Generate insights report with SSE progress events."""

    async def event_generator():
        steps = [
            ("anomalias", "Detectando anomalias..."),
            ("tendencias", "Analizando tendencias..."),
            ("benchmarking", "Comparando zonas..."),
            ("correlaciones", "Buscando correlaciones..."),
            ("oportunidades", "Identificando oportunidades..."),
            ("narrative", "Generando reporte narrativo..."),
        ]
        total_steps = len(steps)
        all_findings = []

        # Step 1-5: Run detectors sequentially with progress events
        detectors = {
            "anomalias": service.detect_anomalies,
            "tendencias": service.detect_trends,
            "benchmarking": service.detect_benchmarking,
            "correlaciones": service.detect_correlations,
            "oportunidades": service.detect_opportunities,
        }

        for i, (step_name, step_label) in enumerate(steps[:-1]):
            yield {
                "event": "progress",
                "data": json.dumps({
                    "step": step_name,
                    "label": step_label,
                    "status": "running",
                    "step_number": i + 1,
                    "total_steps": total_steps,
                }),
            }

            try:
                findings = detectors[step_name]()
                all_findings.extend(findings)
            except Exception as e:
                logger.error("Detector %s failed: %s", step_name, e)

            yield {
                "event": "progress",
                "data": json.dumps({
                    "step": step_name,
                    "label": step_label,
                    "status": "done",
                    "findings_count": len([f for f in all_findings if f.category == step_name]),
                    "step_number": i + 1,
                    "total_steps": total_steps,
                }),
            }

        # Delegate report building to the service (handles dedup, cap, scoring)
        from app.services.insights_config import SEVERITY_MAGNITUDE_CAP, CATEGORY_WEIGHTS, MAX_FINDINGS_PER_CATEGORY, MAX_TOTAL_FINDINGS

        # Cap magnitude to prevent outliers
        for f in all_findings:
            if abs(f.magnitude) > SEVERITY_MAGNITUDE_CAP:
                f.magnitude = SEVERITY_MAGNITUDE_CAP if f.magnitude > 0 else -SEVERITY_MAGNITUDE_CAP
                f.severity = SEVERITY_MAGNITUDE_CAP * CATEGORY_WEIGHTS.get(f.category, 1.0)

        # Deduplicate
        seen: set[tuple[str, str, str]] = set()
        deduped = []
        for f in all_findings:
            key = (f.zone or "", f.metrics[0] if f.metrics else "", f.category)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        # Limit per category with metric diversity
        from app.services.insights_config import MAX_FINDINGS_PER_METRIC_PER_CATEGORY
        capped = []
        for cat in CATEGORY_WEIGHTS:
            cat_f = sorted([f for f in deduped if f.category == cat], key=lambda f: f.severity, reverse=True)
            metric_counts: dict[str, int] = {}
            selected = []
            for f in cat_f:
                mk = f.metrics[0] if f.metrics else ""
                cnt = metric_counts.get(mk, 0)
                if cnt >= MAX_FINDINGS_PER_METRIC_PER_CATEGORY:
                    continue
                metric_counts[mk] = cnt + 1
                selected.append(f)
                if len(selected) >= MAX_FINDINGS_PER_CATEGORY:
                    break
            capped.extend(selected)
        capped.sort(key=lambda f: f.severity, reverse=True)
        all_findings = capped[:MAX_TOTAL_FINDINGS]

        # Build report
        from uuid import uuid4
        from app.models.schemas import InsightReport

        report = InsightReport(
            id=f"report_{uuid4().hex[:8]}",
            findings=all_findings,
            category_counts={
                cat: sum(1 for f in all_findings if f.category == cat)
                for cat in CATEGORY_WEIGHTS
            },
        )

        # Step 6: Generate LLM narrative
        yield {
            "event": "progress",
            "data": json.dumps({
                "step": "narrative",
                "label": "Generando reporte narrativo...",
                "status": "running",
                "step_number": total_steps,
                "total_steps": total_steps,
            }),
        }

        narrative = service.generate_narrative(report)
        report.markdown_report = narrative

        # Parse narrative into sections for the frontend
        sections = service.parse_narrative_sections(narrative)
        report.narrative_sections = sections
        report.executive_summary = sections.get("resumen", "")

        # Cache the report
        service._cached_report = report

        yield {
            "event": "progress",
            "data": json.dumps({
                "step": "narrative",
                "label": "Reporte listo",
                "status": "done",
                "step_number": total_steps,
                "total_steps": total_steps,
            }),
        }

        # Send complete report
        yield {
            "event": "report",
            "data": report.model_dump_json(),
        }

        yield {"event": "done", "data": json.dumps({})}

    return EventSourceResponse(event_generator())


@router.get("/report")
async def get_report(
    service: InsightsService = Depends(get_insights_service),
):
    """Return cached insights report, or 404 if none generated yet."""
    report = service.get_cached_report()
    if report is None:
        return {"report": None, "message": "No report generated yet"}
    return {
        "report": report.model_dump(),
        "generated_at": report.generated_at.isoformat(),
        "cached": True,
    }
