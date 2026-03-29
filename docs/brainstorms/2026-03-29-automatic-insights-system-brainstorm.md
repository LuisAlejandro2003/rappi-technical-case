# Brainstorm: Sistema de Insights Automaticos (Section 2.2)

**Date**: 2026-03-29
**Status**: Approved
**Weight**: 30% of evaluation

## What We're Building

An automatic insights detection and reporting system that analyzes operational data and generates a structured executive report. The system runs as an extension of the existing chatbot — same backend, same frontend, new pipeline.

### Five Insight Categories

1. **Anomalias**: Zones with drastic week-over-week changes (>10% deterioration/improvement)
2. **Tendencias Preocupantes**: Metrics in consistent decline (3+ consecutive weeks)
3. **Benchmarking**: Comparison of similar zones (same country/type) with divergent performance
4. **Correlaciones**: Relationships between metrics (e.g., low Lead Penetration + low Conversion)
5. **Oportunidades**: General opportunities detected from data patterns

### Report Structure

- Executive summary: Top 3-5 critical findings
- Detail per insight category
- Actionable recommendations per finding
- Output: Markdown rendered in UI

## Why This Approach

### Architecture: Hybrid Pipeline + LLM Narrative

**Detection layer**: Python service with deterministic SQL queries per category. Each detector is a method that runs SQL against DuckDB and returns structured findings.

**Narrative layer**: LLM (Claude) receives the structured findings and generates the executive report with business context, interpretation, and actionable recommendations.

**Why not pure LLM?** The LLM should not be responsible for detecting a -15% anomaly — that's a SQL comparison. Deterministic detection = reliable, reproducible, testable results. The LLM adds value where it excels: synthesizing findings into narrative and generating business recommendations.

**Why not pure pipeline?** A pipeline alone produces dry data tables. The LLM transforms "Zone X: Perfect Order dropped 18% WoW" into "Chapinero experienced a significant operational deterioration that may be linked to logistics capacity constraints — recommend investigating courier availability."

### Rappi's Own Guidance

> "Prioriza relevancia sobre complejidad. 5 insights bien fundamentados y accionables valen mas que 20 insights superficiales."

This validates SQL-with-heuristics over scipy/numpy statistical analysis. Calibrated thresholds + business context > complex statistics.

## Key Decisions

### 1. UI: Sidebar Tab (not in chat)

The report lives in a dedicated "Insights" tab in the sidebar. Clicking shows the structured report in the main area. A "Generar Reporte" button triggers the pipeline.

**Why not in chat?** The enunciado says "analice automaticamente" — forcing users to type a command contradicts "automatic". The report has rigid structure (5 categories, executive summary) that doesn't fit a conversational medium.

### 2. Integration: Insights -> Chat (one-directional + context injection)

Each insight has an "Explorar en chat" button that opens the chatbot with a pre-crafted question for deeper analysis. This is 100% deterministic — no LLM routing logic.

Additionally, the latest insights summary is injected into the chat's system prompt so the LLM naturally references findings when relevant.

**Why not bidirectional?** The chat -> insights direction requires the LLM to "detect" when to suggest the report. This is unreliable and can fail during a live demo. The risk/reward ratio is bad.

### 3. Output: Markdown Rendered in UI

Uses the existing MarkdownRenderer component. No PDF generation (heavy dependency, fragile styling, marginal gain for a technical evaluation).

### 4. Statistics: SQL Pure with Heuristics

- Anomalies: `(L0W - L1W) / L1W > threshold` in SQL
- Trends: Check 3+ consecutive weeks of decline via window functions or column comparisons
- Benchmarking: Compare zones within same COUNTRY where one metric diverges >X% from peer average
- Correlations: Co-occurrence heuristics (zones where metric A < threshold AND metric B < threshold). DuckDB's `CORR()` available as enhancement if needed
- Opportunities: Zones with improving trends or underperformance gaps that suggest easy wins

### 5. Service Architecture

New `InsightsService` following existing patterns:
- Instantiated in `dependencies.py` as singleton
- Uses `DuckDBService` for queries (same as `QueryService`)
- Uses `LLMProvider` for narrative generation
- New endpoint: `GET /insights/report` or `POST /insights/generate`
- New Jinja2 template for insights LLM prompt

### 6. Caching: Generate Once, Cache in Memory

Pipeline runs on first request, result cached in memory (or SQLite). Subsequent requests return instantly. "Regenerar" button available to force re-execution. Data is static CSVs — no reason to recompute.

### 7. Severity Scoring

Each insight gets a simple severity score: `magnitude_of_change(%) * category_priority_weight`. Category weights: anomalies (highest) > worrying trends > benchmarking gaps > correlations > opportunities. Top 3-5 by score go to the executive summary. Demonstrates "attention to detail" in evaluation.

## Design Reference

**Figma Make**: https://www.figma.com/make/Y8jxLwGDPSoVPUoM19ID2n/Rappi-Operations-Analytics-Chatbot

The UI design was generated using an AI design tool with the Rappi brand palette. The implementation plan must include a phase that uses Figma MCP's `get_design_context` to extract the design and adapt it to the existing Next.js/Tailwind architecture following established component patterns.

## Next Steps

Run `/workflows:plan` to define implementation phases, file changes, and test strategy.
