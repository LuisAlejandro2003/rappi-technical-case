---
title: "feat: Automatic Insights System"
type: feat
date: 2026-03-29
---

# feat: Automatic Insights System (Section 2.2)

## Overview

Automatic insights detection and executive report generation for the Rappi Analytics Chatbot. A Python pipeline runs deterministic SQL queries to detect anomalies, trends, benchmarking gaps, correlations, and opportunities. An LLM synthesizes findings into a narrative executive report with actionable recommendations. The report lives in a dedicated "Insights" tab in the UI, with integration to the chat via "Explorar en chat" buttons.

**Weight**: 30% of evaluation score (Calidad de Insights)
**Design reference**: [Figma Make](https://www.figma.com/make/Y8jxLwGDPSoVPUoM19ID2n/Rappi-Operations-Analytics-Chatbot)
**Brainstorm**: `docs/brainstorms/2026-03-29-automatic-insights-system-brainstorm.md`

## Problem Statement / Motivation

SP&A and Operations teams need automated identification of critical operational patterns without manually querying data. The current chatbot answers questions reactively; the insights system proactively surfaces what matters most.

Rappi's own guidance: **"Prioriza relevancia sobre complejidad. 5 insights bien fundamentados y accionables valen mas que 20 insights superficiales."**

## Technical Approach

### Architecture

```
[User clicks "Generar Reporte"]
        |
        v
[InsightsService.generate_report()]
        |
        v
[5 SQL Detectors] ──> [Structured Findings] ──> [LLM Narrative] ──> [Cached Report]
  (deterministic)       (list[Insight])           (Claude)            (in-memory)
        |                                            |
        v                                            v
  [SSE: progress]                              [SSE: report_ready]
```

**Why hybrid?** Deterministic SQL guarantees reproducible, testable detection. The LLM adds business interpretation and recommendations — where it excels. Neither alone is sufficient.

### Metric Polarity Table

Required by anomalies, trends, and opportunities detectors. Derived from metrics dictionary.

| Metric | Polarity | Rationale |
|--------|----------|-----------|
| Perfect Orders | higher_is_better | More perfect orders = better service |
| Gross Profit UE | higher_is_better | Higher margin per order = more profitable |
| Lead Penetration | higher_is_better | More leads = better coverage |
| Pro Adoption | higher_is_better | More Pro users = better retention |
| Turbo Adoption | higher_is_better | More Turbo usage = faster delivery preference |
| Restaurants SST > SS CVR | higher_is_better | Higher funnel conversion |
| Restaurants SS > ATC CVR | higher_is_better | Higher funnel conversion |
| Restaurants ATC > Trx CVR | higher_is_better | Higher funnel conversion |
| % Order Loss | lower_is_better | Less order loss = better ops |
| % PRO Users Who Breakeven | higher_is_better | More breakeven = sustainable Pro |
| Restaurants Markdowns / GMV | lower_is_better | Less markdowns = better pricing |
| Orders (raw_orders) | higher_is_better | More orders = more business |

This table is hardcoded as a Python dict in the insights service config.

### Severity Scoring Formula

```python
severity = abs(magnitude) * category_weight * metric_importance
```

**Category weights** (sum to 1.0 not required — these are multipliers):

| Category | Weight | Rationale |
|----------|--------|-----------|
| Anomalias | 1.0 | Immediate action needed |
| Tendencias | 0.9 | Sustained deterioration is urgent |
| Benchmarking | 0.7 | Comparative gaps indicate potential |
| Correlaciones | 0.6 | Structural relationships |
| Oportunidades | 0.5 | Positive signals, lower urgency |

**Magnitude calculation per category**:
- **Anomalias**: `abs((L0W - L1W) / L1W)` — WoW relative change. Guard: if L1W == 0, use absolute change instead.
- **Tendencias**: Sum of consecutive weekly declines (e.g., if 4 consecutive weeks of decline, sum all 4 deltas). Gives larger magnitude to longer/steeper declines.
- **Benchmarking**: `abs(zone_value - peer_median) / peer_median` — divergence from peer group median.
- **Correlaciones**: Average of the two metrics' deviation below peer median. E.g., if Lead Penetration is 20% below median and Conversion is 15% below, magnitude = 0.175.
- **Oportunidades**: Same as trends but for improvement direction.

**Metric importance** (optional multiplier, default 1.0): Can assign higher weight to business-critical metrics (Perfect Orders, Gross Profit) later. For MVP, all 1.0.

**Normalization**: Scores are NOT normalized to 0-100. Raw scores are used for ranking (top N). The absolute value doesn't matter — only relative order matters for the executive summary.

**Tie-breaking**: If scores are equal, order by: (1) category weight desc, (2) alphabetical zone name.

### Detector Specifications

#### 1. Anomalias Detector

```sql
-- For raw_input_metrics
SELECT ZONE, CITY, COUNTRY, METRIC, L0W_ROLL, L1W_ROLL,
       (L0W_ROLL - L1W_ROLL) AS abs_change,
       CASE WHEN L1W_ROLL != 0
            THEN (L0W_ROLL - L1W_ROLL) / ABS(L1W_ROLL)
            ELSE NULL END AS pct_change
FROM raw_input_metrics
WHERE ABS(CASE WHEN L1W_ROLL != 0
               THEN (L0W_ROLL - L1W_ROLL) / ABS(L1W_ROLL)
               ELSE 999 END) > 0.10

-- For raw_orders (same pattern with L0W, L1W)
```

**Threshold**: >10% relative WoW change (as specified in requirements).
**Edge cases**: L1W_ROLL = 0 → flag as anomaly if L0W_ROLL != 0 (something from nothing). Both = 0 → skip.
**Polarity**: Use metric polarity table to classify as "improvement" or "deterioration".

#### 2. Tendencias Detector

```sql
-- Check 3+ consecutive declining weeks
-- For a "higher_is_better" metric, declining means each week < previous
SELECT ZONE, CITY, COUNTRY, METRIC,
       L3W_ROLL, L2W_ROLL, L1W_ROLL, L0W_ROLL
FROM raw_input_metrics
WHERE L0W_ROLL < L1W_ROLL
  AND L1W_ROLL < L2W_ROLL
  AND L2W_ROLL < L3W_ROLL
```

**Minimum magnitude filter**: Total decline over the period must be > 5% relative. This avoids flagging micro-fluctuations (0.500 → 0.499 → 0.498).
**Polarity**: For `lower_is_better` metrics, invert the comparison (increasing = deteriorating).
**Extended check**: Also check 4+ and 5+ week declines for higher severity.

#### 3. Benchmarking Detector

```sql
-- Compare zone performance to peer group (same COUNTRY)
WITH peer_stats AS (
    SELECT COUNTRY, METRIC,
           MEDIAN(L0W_ROLL) AS peer_median,
           STDDEV(L0W_ROLL) AS peer_std,
           COUNT(*) AS peer_count
    FROM raw_input_metrics
    GROUP BY COUNTRY, METRIC
    HAVING COUNT(*) >= 3  -- minimum peer group size
)
SELECT rim.ZONE, rim.CITY, rim.COUNTRY, rim.METRIC,
       rim.L0W_ROLL AS zone_value,
       ps.peer_median,
       (rim.L0W_ROLL - ps.peer_median) / NULLIF(ABS(ps.peer_median), 0) AS divergence
FROM raw_input_metrics rim
JOIN peer_stats ps ON rim.COUNTRY = ps.COUNTRY AND rim.METRIC = ps.METRIC
WHERE ABS((rim.L0W_ROLL - ps.peer_median) / NULLIF(ABS(ps.peer_median), 0)) > 0.20
```

**Threshold**: >20% divergence from peer median (same country).
**Minimum group size**: 3 zones. Skip groups smaller than that.
**Polarity-aware**: For `higher_is_better`, flag zones BELOW median. For `lower_is_better`, flag zones ABOVE median.

#### 4. Correlaciones Detector

Hardcoded metric pairs with co-occurrence check:

```python
CORRELATED_PAIRS = [
    ("Lead Penetration", "Restaurants SST > SS CVR"),     # Low leads → low funnel start
    ("Restaurants SS > ATC CVR", "Restaurants ATC > Trx CVR"),  # Funnel stages correlate
    ("Perfect Orders", "% Order Loss"),                    # Inverse: low PO ↔ high loss
    ("Pro Adoption", "Gross Profit UE"),                   # Pro users affect profitability
]
```

```sql
-- For each pair, find zones where BOTH metrics are below peer median
WITH medians AS (
    SELECT COUNTRY, METRIC, MEDIAN(L0W_ROLL) AS med
    FROM raw_input_metrics
    GROUP BY COUNTRY, METRIC
)
SELECT a.ZONE, a.CITY, a.COUNTRY,
       a.METRIC AS metric_a, a.L0W_ROLL AS value_a, ma.med AS median_a,
       b.METRIC AS metric_b, b.L0W_ROLL AS value_b, mb.med AS median_b
FROM raw_input_metrics a
JOIN raw_input_metrics b ON a.ZONE = b.ZONE AND a.COUNTRY = b.COUNTRY
JOIN medians ma ON a.COUNTRY = ma.COUNTRY AND a.METRIC = ma.METRIC
JOIN medians mb ON b.COUNTRY = mb.COUNTRY AND b.METRIC = mb.METRIC
WHERE a.METRIC = '{pair[0]}' AND b.METRIC = '{pair[1]}'
  AND a.L0W_ROLL < ma.med AND b.L0W_ROLL < mb.med
```

**Special case for inverse pairs** (Perfect Orders / % Order Loss): Flag when PO is below median AND Order Loss is above median.

#### 5. Oportunidades Detector

Two sub-detectors:
1. **Improving trends**: Inverse of Tendencias — 3+ weeks of consecutive improvement. Uses same SQL pattern with flipped comparisons.
2. **Underperformance gaps with easy wins**: Zones where one key metric is >15% below peer median but most other metrics are at or above median. These zones have specific, addressable weaknesses.

```sql
-- Zones with exactly 1 metric significantly below median (targeted improvement opportunity)
WITH zone_scores AS (
    SELECT rim.ZONE, rim.COUNTRY, rim.METRIC,
           CASE WHEN (rim.L0W_ROLL - ps.peer_median) / NULLIF(ABS(ps.peer_median), 0) < -0.15
                THEN 1 ELSE 0 END AS below_threshold
    FROM raw_input_metrics rim
    JOIN peer_stats ps ON rim.COUNTRY = ps.COUNTRY AND rim.METRIC = ps.METRIC
)
SELECT ZONE, COUNTRY, COUNT(*) AS weak_metrics
FROM zone_scores WHERE below_threshold = 1
GROUP BY ZONE, COUNTRY
HAVING COUNT(*) <= 2  -- 1-2 weak areas = targeted opportunity
```

### API Contract

#### Endpoints

**`POST /insights/generate`** — Triggers report generation. Returns SSE stream with progress events.

```
SSE Events:
  event: progress    data: {"step": "anomalias", "status": "running", "step_number": 1, "total_steps": 6}
  event: progress    data: {"step": "anomalias", "status": "done", "findings_count": 8, "step_number": 1, "total_steps": 6}
  event: progress    data: {"step": "tendencias", "status": "running", "step_number": 2, "total_steps": 6}
  ...
  event: progress    data: {"step": "narrative", "status": "running", "step_number": 6, "total_steps": 6}
  event: report      data: {<InsightReport JSON>}
  event: done        data: {}
```

**`GET /insights/report`** — Returns cached report if available.

```json
// Response 200
{
  "report": {<InsightReport>},
  "generated_at": "2026-03-29T10:30:00Z",
  "cached": true
}

// Response 404 (no report generated yet)
{
  "report": null,
  "message": "No report generated yet"
}
```

#### Schemas

```python
class Insight(BaseModel):
    id: str
    category: Literal["anomalias", "tendencias", "benchmarking", "correlaciones", "oportunidades"]
    severity: float
    title: str
    description: str
    zone: str | None = None
    country: str | None = None
    metrics: list[str]
    magnitude: float
    direction: Literal["improvement", "deterioration", "neutral"]
    recommendation: str
    explore_query: str  # Pre-crafted question for "Explorar en chat"

class InsightReport(BaseModel):
    id: str
    generated_at: datetime
    executive_summary: str  # LLM-generated markdown
    findings: list[Insight]
    category_counts: dict[str, int]
    markdown_report: str  # Full LLM-generated report in markdown
```

### Integration: "Explorar en Chat"

- **Behavior**: Prefills chat input (does NOT auto-send). User can edit before sending.
- **Session**: Creates a new chat session to avoid polluting existing context.
- **Question template**: Generated per finding during detection phase.

```python
# Example explore_query generation per category
anomaly_query = f"Analiza por que {zone} ({country}) tuvo un cambio de {magnitude:.1f}% en {metric} esta semana. Que factores podrian explicarlo?"
trend_query = f"La zona {zone} ha tenido {n_weeks} semanas consecutivas de deterioro en {metric}. Muestra la evolucion y posibles causas."
benchmark_query = f"Compara {zone} con otras zonas de {country} en {metric}. Esta {abs(divergence):.0f}% por debajo del promedio."
```

### System Prompt Cache Invalidation

Current `ChatService.build_system_prompt()` caches permanently (line 128). To inject insights summary:

```python
def build_system_prompt(self, insights_summary: str | None = None) -> str:
    # Always rebuild if insights_summary changes
    if self._system_prompt is None or insights_summary != self._last_insights_summary:
        schema_ctx = self.query_service.get_schema_context()
        data_profile = self.data_profiler.build_profile() if self.data_profiler else ""
        template = _jinja_env.get_template("system_prompt.j2")
        self._system_prompt = template.render(
            schema_context=schema_ctx,
            data_profile=data_profile,
            insights_summary=insights_summary or "",
        )
        self._last_insights_summary = insights_summary
    return self._system_prompt
```

Add `{{ insights_summary }}` block to `system_prompt.j2` template.

### Caching Strategy

- **Storage**: In-memory on `InsightsService` instance (singleton via `dependencies.py`).
- **Invalidation**: Manual only ("Regenerar" button). Data is static CSVs — no auto-invalidation needed.
- **Server restart**: Cache lost. User clicks "Generar" again. Acceptable for this use case.
- **Scope**: Global (single-user app, no auth).

### Loading UX

6 steps displayed sequentially:

| Step | Label | Description |
|------|-------|-------------|
| 1 | Detectando anomalias | Anomaly detector SQL |
| 2 | Analizando tendencias | Trend detector SQL |
| 3 | Comparando zonas | Benchmarking detector SQL |
| 4 | Buscando correlaciones | Correlation detector SQL |
| 5 | Identificando oportunidades | Opportunity detector SQL |
| 6 | Generando reporte narrativo | LLM narrative call |

Steps 1-5 should be fast (<1s each). Step 6 is the bottleneck (5-15s for LLM).

**Timeout**: 60 seconds total. If exceeded, return partial results with error message.
**Cancellation**: Not needed for MVP — generation is fast enough.

---

## Implementation Phases

### Phase 1: Backend — Insights Detection Pipeline

**Goal**: `InsightsService` with 5 detectors that return structured `Insight` objects.

**Tests First** (TDD):
- `test_insights_service.py`
  - `test_detect_anomalies_flags_10pct_change`
  - `test_detect_anomalies_handles_zero_baseline`
  - `test_detect_anomalies_respects_polarity`
  - `test_detect_trends_3_consecutive_weeks`
  - `test_detect_trends_ignores_micro_changes`
  - `test_detect_trends_inverts_for_lower_is_better`
  - `test_detect_benchmarking_divergent_zones`
  - `test_detect_benchmarking_skips_small_groups`
  - `test_detect_correlations_co_occurrence`
  - `test_detect_correlations_inverse_pairs`
  - `test_detect_opportunities_improving_trends`
  - `test_detect_opportunities_targeted_weakness`
  - `test_severity_scoring_ranks_correctly`
  - `test_generate_explore_queries`

**Files**:
- `backend/app/services/insights_service.py` — New service (InsightsService class)
- `backend/app/models/schemas.py` — Add Insight + InsightReport models
- `backend/app/services/insights_config.py` — New: metric polarity, category weights, thresholds, correlated pairs
- `backend/tests/test_insights_service.py` — New test file

**Acceptance Criteria**:
- [ ] Each detector returns `list[Insight]` with severity scores
- [ ] Metric polarity is respected (improvements vs deteriorations classified correctly)
- [ ] Edge cases handled: zero baselines, NULL values, small peer groups
- [ ] All SQL queries use DuckDB-compatible syntax
- [ ] Severity scoring produces deterministic ranking
- [ ] `explore_query` is generated for each finding

### Phase 2: Backend — LLM Narrative + API Endpoints

**Goal**: LLM generates executive report from findings. SSE endpoint for generation, GET for cached report.

**Tests First**:
- `test_insights_narrative.py`
  - `test_generate_narrative_with_findings`
  - `test_generate_narrative_empty_findings`
  - `test_narrative_is_spanish`
- `test_insights_router.py`
  - `test_generate_endpoint_returns_sse`
  - `test_get_report_returns_cached`
  - `test_get_report_404_when_no_cache`
  - `test_regenerate_invalidates_cache`

**Files**:
- `backend/app/templates/insights_prompt.j2` — New Jinja2 template for LLM narrative prompt
- `backend/app/routers/insights.py` — New router with POST /generate and GET /report
- `backend/app/dependencies.py` — Add `get_insights_service()`
- `backend/app/main.py` — Register insights router
- `backend/app/services/chat_service.py` — Modify `build_system_prompt()` to accept insights_summary
- `backend/app/templates/system_prompt.j2` — Add `{{ insights_summary }}` block
- `backend/tests/test_insights_narrative.py` — New
- `backend/tests/test_insights_router.py` — New

**Acceptance Criteria**:
- [ ] LLM generates markdown report in Spanish
- [ ] Report has: executive summary (top 3-5), detail per category, recommendations
- [ ] SSE stream emits progress events per detection step
- [ ] GET endpoint returns cached report instantly
- [ ] POST endpoint regenerates and updates cache
- [ ] Insights summary injected into chat system prompt after generation
- [ ] Chat system prompt cache invalidated on new insights report

### Phase 3: Frontend — Figma Design Extraction + Insights UI

**Goal**: Use Figma MCP `get_design_context` to extract the design, then build the Insights tab and report view adapting to existing Next.js/Tailwind patterns.

**Sub-steps**:
1. **Figma extraction**: Use `get_design_context` with the Figma Make file to get component structure, colors, spacing
2. **Adapt to architecture**: Map Figma components to existing patterns (Sidebar tabs, MarkdownRenderer, card components)
3. **Build components**: Insights tab, report view, summary cards, category sections, loading state, empty state

**Files**:
- `frontend/src/stores/insights-store.ts` — New Zustand store for insights state
- `frontend/src/types/api.ts` — Add Insight, InsightReport types
- `frontend/src/lib/api.ts` — Add insights API functions (fetchReport, generateReport SSE)
- `frontend/src/components/layout/sidebar.tsx` — Add Chat/Insights tab switching
- `frontend/src/features/insights/components/insights-view.tsx` — New: main report view
- `frontend/src/features/insights/components/summary-cards.tsx` — New: 5 category metric cards
- `frontend/src/features/insights/components/category-section.tsx` — New: collapsible category detail
- `frontend/src/features/insights/components/insight-card.tsx` — New: individual finding card
- `frontend/src/features/insights/components/insights-loading.tsx` — New: step-by-step loading
- `frontend/src/features/insights/components/insights-empty.tsx` — New: empty state with CTA
- `frontend/src/features/insights/hooks/use-insights-stream.ts` — New: SSE hook for generation
- `frontend/src/app/page.tsx` — Add conditional rendering: Chat view vs Insights view

**Acceptance Criteria**:
- [ ] Sidebar has Chat / Insights tabs with active indicator
- [ ] Empty state shown when no report exists
- [ ] "Generar Reporte" button triggers SSE generation with step indicators
- [ ] Report displays: summary cards, executive summary, collapsible category sections
- [ ] Each insight card shows: title, severity badge, description, recommendation, "Explorar en chat" button
- [ ] "Explorar en chat" switches to Chat tab, creates new session, prefills input
- [ ] Responsive: cards stack on mobile, sections are full-width
- [ ] Cached report loads instantly on subsequent tab visits
- [ ] "Regenerar" button available after report is generated
- [ ] No emojis — icons only (Lucide)

### Phase 4: Integration + Polish

**Goal**: Wire insights → chat integration, edge cases, final polish.

**Tasks**:
- [ ] "Explorar en chat" creates new session + prefills input + switches tab
- [ ] Chat system prompt includes insights summary when available
- [ ] Handle edge case: all detectors return 0 findings → show "No se encontraron hallazgos significativos" with lower-threshold suggestions
- [ ] Handle LLM timeout: return partial results (structured findings without narrative)
- [ ] Generated timestamp shown in report header
- [ ] Test full flow end-to-end: generate → view → explore in chat → chat has context

**Files modified**:
- `frontend/src/app/page.tsx` — Tab state management, explore-in-chat handler
- `frontend/src/stores/insights-store.ts` — Explore action that creates session
- `backend/app/services/insights_service.py` — Edge cases, timeout handling
- `backend/app/services/chat_service.py` — Read insights summary from InsightsService

---

## Alternative Approaches Considered

### Pure LLM (rejected)
Let the LLM run multiple queries to "discover" insights. Rejected because: non-deterministic detection, unreproducible results, slower, harder to test, and the LLM might miss patterns that simple SQL catches reliably.

### Pure Pipeline without LLM (rejected)
Generate the entire report with Python string formatting. Rejected because: produces dry, repetitive text. The LLM adds genuine value in business interpretation and contextual recommendations.

### PDF export (rejected)
WeasyPrint or similar for PDF generation. Rejected because: heavy dependency, fragile styling, high implementation risk for marginal demo value. Markdown rendered in UI looks identical for evaluation purposes.

### Bidirectional chat integration (rejected)
Chat → insights routing (LLM suggests "see insights report"). Rejected because: unreliable LLM routing can fail during demo. One-directional (insights → chat via buttons) is deterministic and sufficient.

---

## Dependencies & Prerequisites

- [ ] Section 2.1 (Chat Bot) fully functional — already done
- [ ] DuckDB loaded with all 3 CSV tables — already done
- [ ] LLM Provider working — already done
- [ ] Figma Make design available — done (link in brainstorm)

## Risk Analysis & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LLM narrative timeout | Medium | Medium | Return structured findings without narrative; show partial results |
| Too many findings (noisy) | Medium | High | Severity scoring + top-N filtering. Calibrate thresholds against real data |
| Too few findings | Low | High | Lower thresholds if <3 total findings. Always surface at least top opportunities |
| Metric polarity wrong | Low | Critical | Validate against Rappi's metrics dictionary. Unit test each metric |
| Figma design doesn't match architecture | Low | Medium | Adapt design to existing patterns, don't force pixel-perfect |
| System prompt too long with insights summary | Low | Medium | Keep summary concise: max 500 tokens, just top 5 findings as bullet points |

## Success Metrics

- [ ] 5 insight categories produce relevant, non-trivial findings from real data
- [ ] Executive summary highlights 3-5 most critical findings
- [ ] Each recommendation is specific and actionable (not generic advice)
- [ ] Report generates in <30 seconds
- [ ] "Explorar en chat" seamlessly transitions to deeper analysis
- [ ] UI is clean, professional, and consistent with existing chat design

## References & Research

### Internal References
- Data Profiler pattern: `backend/app/services/data_profiler.py`
- Service DI pattern: `backend/app/dependencies.py`
- SSE streaming pattern: `backend/app/routers/chat.py:15-22`
- LLM Provider interface: `backend/app/services/llm_provider.py`
- Sidebar component: `frontend/src/components/layout/sidebar.tsx`
- Session store pattern: `frontend/src/stores/session-store.ts`
- Jinja2 templates: `backend/app/templates/`

### Design
- Figma Make: https://www.figma.com/make/Y8jxLwGDPSoVPUoM19ID2n/Rappi-Operations-Analytics-Chatbot
- Brainstorm: `docs/brainstorms/2026-03-29-automatic-insights-system-brainstorm.md`
- Phase 3 includes Figma MCP `get_design_context` extraction step
