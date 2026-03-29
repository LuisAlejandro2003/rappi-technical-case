# Rappi Operations Analytics Chatbot

Natural-language-to-SQL analytics chatbot for Rappi operations data. Ask questions in plain language and get instant answers backed by SQL queries against operational datasets.

## Architecture

- **Backend**: FastAPI + DuckDB + Anthropic Claude (Python 3.12, managed with uv)
- **Frontend**: Next.js 14 + Tailwind CSS + Recharts (TypeScript)
- **Data**: DuckDB over CSV files (RAW_ORDERS, RAW_SUMMARY, RAW_INPUT_METRICS)

## Quick Start with Docker Compose

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Health check: http://localhost:8000/health

## Local Development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Business Context Architecture

The chatbot understands operational business language through three layers that work together:

### 1. Business Glossary (static)

A Jinja2 template (`backend/app/templates/business_context.j2`) maps operational terminology to data logic. For example, "cobertura" maps to the Lead Penetration metric, "zonas en riesgo" maps to zones with declining trends over consecutive weeks. This allows non-technical users to ask questions in their natural business language without knowing column names or SQL syntax.

### 2. Few-Shot SQL Examples (static)

Five representative question-to-SQL pairs teach the LLM how to translate different types of analytical questions: rankings, comparisons, temporal trends, aggregations, and multi-metric analysis. The LLM generalizes these patterns to handle questions it hasn't seen before.

### 3. Dynamic Data Profiler (runtime)

The `DataProfiler` service (`backend/app/services/data_profiler.py`) runs SQL queries against the actual dataset at startup and generates a statistical summary that is injected into the LLM's system prompt. This summary includes:

- **Metric distributions by country** — current averages for key KPIs across all 9 markets
- **Trend directions** — whether each metric is improving or declining vs 4 weeks ago
- **Outlier zones** — the zones with the largest recent declines and the best current performance
- **Order volume by market** — scale of operations and growth/contraction per country
- **Data glossary** — column definitions loaded from RAW_SUMMARY.csv

This gives the LLM a real-time understanding of the current state of the business. When a user asks "how is Brazil doing?", the LLM already has the statistical context to provide an informed analysis — it knows the baselines, the trends, and the outliers. As the underlying data changes, the profile is automatically recalculated on the next backend restart.

The profiler does not replace query execution. It provides the analytical context that allows the LLM to interpret query results with the same situational awareness that a human analyst would have after reviewing a dashboard.

### Prompt Engineering

System prompts are managed as modular Jinja2 templates (`backend/app/templates/`), separating content from application logic:

```
backend/app/templates/
  system_prompt.j2        # Main template — role, schema, SQL guidelines
  business_context.j2     # Glossary, metric thresholds, few-shot examples
  response_rules.j2       # Formatting, analysis depth, output rules
```

Dynamic context (schema DDL, data profile) is injected as template variables at render time.

## Project Structure

```
backend/
  app/
    core/       # Config, database
    models/     # Pydantic schemas
    services/   # Business logic (Claude, DuckDB, query pipeline, data profiler)
    templates/  # Jinja2 prompt templates
    routers/    # API endpoints
    main.py     # FastAPI application
  tests/
frontend/
  src/app/      # Next.js app router pages
data/           # CSV data files
docs/           # Project documentation
```
