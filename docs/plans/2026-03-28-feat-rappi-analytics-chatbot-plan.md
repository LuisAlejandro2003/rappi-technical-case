---
title: "feat: Rappi Operations Analytics Chatbot"
type: feat
date: 2026-03-28
---

# Rappi Operations Analytics Chatbot

## Overview

Conversational AI system that lets non-technical users (SP&A and Operations teams) query Rappi's operational metrics in natural language. The bot translates questions to SQL, executes against DuckDB, and returns formatted responses with interactive visualizations.

This is a technical evaluation for an AI Engineer position. Clean code, solid architecture, and well-justified decisions are critical.

## Problem Statement

Rappi operates in 9 countries with hundreds of zones. Teams need data-driven decisions but face:
1. **Fragmented access**: Extracting insights requires SQL/Python knowledge
2. **Repetitive analysis**: Weekly hours spent identifying problematic zones and opportunities

## Proposed Solution

A hybrid Text-to-SQL chatbot where the LLM acts as a translator (NL to SQL), never as a calculator. Deterministic computation happens in DuckDB. The pipeline:

```
User question → LLM generates SQL → sqlglot validates → DuckDB executes → LLM formats response → SSE streams to frontend
```

## Development Methodology

### Test-Driven Development (TDD)

Every phase follows the Red-Green-Refactor cycle:
1. **Red**: Write tests that define the expected behavior BEFORE implementation
2. **Green**: Write the minimum code to make tests pass
3. **Refactor**: Clean up while keeping tests green

This is especially critical for:
- `query_service.py` — SQL validation edge cases (injection, multi-statement, invalid columns)
- `chat_service.py` — tool loop orchestration, error handling, retry logic
- `session_service.py` — sliding window correctness, summary generation
- `viz_service.py` — chart type detection rules

Each phase below includes a "Tests First" section specifying which tests to write before implementation.

### Docker

The evaluator should be able to run `docker compose up` and have everything working.

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
    env_file: .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
```

Each service gets a Dockerfile:
- `backend/Dockerfile` — Python 3.12 slim, uv install, uvicorn
- `frontend/Dockerfile` — Node 18 alpine, npm install, next build + start

DuckDB is in-process (no separate container needed).

### Design Source: Figma

The UI design lives in Figma Make:
- **URL**: https://www.figma.com/make/Y8jxLwGDPSoVPUoM19ID2n/Rappi-Operations-Analytics-Chatbot
- Frontend implementation must match the Figma design pixel-by-pixel
- Colors, spacing, typography, and component styles come from Figma — not hardcoded
- If Figma MCP is available, use `get_design_context` to extract design tokens
- If not, the user will provide exported code/screenshots from Figma Make

## Technical Approach

### Backend Architecture

**Stack**: FastAPI (Python) + DuckDB + Claude API (Anthropic SDK direct)

**Pattern**: Layered architecture with service layer. No hexagonal/DDD — proportional to scope.

```
backend/
  Dockerfile
  pyproject.toml               # uv + ruff + mypy + pytest config
  app/
    __init__.py
    main.py                    # FastAPI app with lifespan
    dependencies.py            # Depends() factories for DI
    core/
      __init__.py
      config.py                # pydantic-settings (Settings class)
      database.py              # DuckDB connection management (singleton + cursor-per-request)
    models/
      __init__.py
      schemas.py               # Pydantic request/response models
    services/
      __init__.py
      llm_provider.py          # LLMProvider Protocol + ClaudeLLMProvider implementation
      chat_service.py          # Orchestrates LLM calls, session mgmt, tool loop
      query_service.py         # SQL generation, sqlglot validation, DuckDB execution
      session_service.py       # Session CRUD, sliding window memory
      viz_service.py           # Chart type decision + JSON config generation
    routers/
      __init__.py
      chat.py                  # POST /chat/stream (SSE), GET /sessions
      health.py                # GET /health
  tests/
    __init__.py
    conftest.py                # Fixtures: mock settings, in-memory DuckDB, mock LLM
    test_query_service.py      # SQL validation, DuckDB execution
    test_chat_service.py       # Tool loop, response formatting
    test_session_service.py    # Memory window, summarization
    test_viz_service.py        # Chart type detection, config generation
    test_sql_validator.py      # Security: injection vectors
    test_routers.py            # Integration: SSE streaming, session endpoints
  data/
    RAW_INPUT_METRICS.csv
    RAW_ORDERS.csv
```

### Frontend Architecture

**Stack**: Next.js 14+ (App Router) + TypeScript + Tailwind CSS + Zustand + Recharts + Lucide Icons

**Pattern**: Hybrid — flat shared UI components + feature-based domain folders. Not pure Atomic Design (overkill for ~20 components, classification overhead exceeds organizational benefit).

**Why this over Atomic Design**: Atomic Design is a design system methodology, not an application architecture. With 15-20 components, debating "is MessageBubble an atom or molecule?" wastes time. Feature folders (chat/, visualization/) group by business domain, which matches how code changes together.

**State management**: Zustand over React Context. Chat messages are high-frequency state updates — Context would re-render the entire provider tree on every new token during streaming. Zustand's selector pattern avoids this.

```
frontend/
  Dockerfile
  package.json
  tailwind.config.ts
  src/
    app/                           # Next.js App Router (routing ONLY)
      layout.tsx                   # Root layout (providers, global styles, fonts)
      page.tsx                     # Redirect to /chat
      globals.css                  # Tailwind base + Rappi CSS variables
      (chat)/                      # Route group (no URL segment)
        layout.tsx                 # Chat layout with sidebar
        page.tsx                   # Default chat view (new session)
        [sessionId]/
          page.tsx                 # Specific session view

    components/                    # Shared, reusable UI (no business logic)
      ui/                          # Primitives
        button.tsx
        input.tsx
        avatar.tsx
        spinner.tsx
        badge.tsx
      layout/                      # Shell
        sidebar.tsx
        header.tsx
        input-bar.tsx

    features/                      # Domain logic (organized by business domain)
      chat/
        components/
          message-bubble.tsx
          message-list.tsx
          welcome-card.tsx
          typing-indicator.tsx
          suggestion-chip.tsx
          session-list.tsx
        hooks/
          use-chat-stream.ts       # SSE consumption via fetch + ReadableStream
          use-chat-scroll.ts       # Auto-scroll to latest message
        types.ts                   # Message, Session, ChatState
      visualization/
        components/
          dynamic-chart.tsx        # Routes to correct chart by type
          line-chart-card.tsx      # Recharts LineChart wrapper
          bar-chart-card.tsx       # Recharts BarChart wrapper
          data-table.tsx           # Sortable table with export
          chart-container.tsx      # ResponsiveContainer wrapper
          chart-tooltip.tsx        # Custom Recharts tooltip
        hooks/
          use-chart-data.ts        # Transform API data to Recharts format
        types.ts                   # ChartConfig, DataPoint, Series

    stores/                        # Zustand stores
      chat-store.ts                # Messages, streaming state
      session-store.ts             # Active session, session list

    lib/                           # Framework-level utilities
      api.ts                       # Fetch wrapper, base URL config
      cn.ts                        # clsx + tailwind-merge utility

    hooks/                         # Shared hooks (cross-feature)
      use-media-query.ts           # Responsive breakpoint detection

    types/                         # Shared types
      api.ts                       # ApiResponse<T>, SSE event types
```

**File naming**: kebab-case for all files (matches Next.js conventions and shadcn/ui). Component exports are PascalCase.

**Key frontend decisions**:
| Decision | Choice | Why |
|----------|--------|-----|
| Architecture | Hybrid (shared UI + feature folders) | Groups code by business domain (chat, viz), not visual hierarchy |
| State management | Zustand | High-frequency updates (streaming tokens) — Context causes cascading re-renders |
| Styling | Tailwind CSS + `cn()` utility (clsx + tailwind-merge) | Industry standard, zero CSS files per component |
| Component variants | `cva` (class-variance-authority) | Type-safe variants for Button, Badge, etc. |
| Icons | Lucide Icons | Consistent, tree-shakeable, React-native. Zero emojis. |
| Charts | Recharts 3.x with thin wrappers | `"use client"` components with ResponsiveContainer |
| SSE consumption | `fetch()` + ReadableStream | `EventSource` API only supports GET; chat needs POST |

### Key Design Decisions (from brainstorm)

| Decision | Choice | Why |
|----------|--------|-----|
| NL→Query strategy | Hybrid Text-to-SQL | LLM translates, DuckDB computes. SQL is deterministic. Scales to 100M+ rows. |
| Database | DuckDB (not Postgres) | OLAP columnar, in-process, zero-setup. 20x faster for analytical queries. |
| LLM SDK | Anthropic SDK direct (not LangChain) | Shows fundamental understanding. LangChain's SQL agent does 4-5 LLM calls by default. |
| LLM abstraction | `LLMProvider` Protocol | 5-line interface for swapping to GPT-4. Proportional abstraction. |
| Memory | Stateful backend, sliding window | Backend owns history. Last 5-8 turns complete + summary of older. Token-efficient. |
| Visualization | Backend JSON config → Recharts | Secure (no code gen), interactive, clean separation of concerns. |
| Streaming | SSE via FastAPI `EventSourceResponse` | Unidirectional, simpler than WebSocket, native FastAPI 0.135+ support. |
| Project setup | `uv` + `pyproject.toml` + ruff + mypy | Modern Python tooling. Deterministic lockfile. |
| Methodology | TDD (Red-Green-Refactor) | Tests written before implementation. Shows engineering discipline. |
| Deployment | Docker Compose (backend + frontend) | `docker compose up` and everything works. Zero-friction for evaluator. |
| Design source | Figma Make | UI implementation matches Figma design. Colors/spacing/typography from design, not hardcoded. |
| Frontend architecture | Hybrid (shared UI + feature folders) | Groups by business domain (chat, viz), not visual hierarchy. Pragmatic over Atomic Design. |
| Frontend state | Zustand | High-frequency streaming updates — React Context would cause cascading re-renders. |

### Implementation Phases

#### Phase 0: Project Scaffold + Docker

**Goal**: Monorepo structure, Docker Compose, both services start (even if empty).

**Tasks**:

- [ ] Initialize git repo
- [ ] Create monorepo structure: `backend/`, `frontend/`, `data/`, `docs/`, `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`
- [ ] Move CSV files to `data/`
- [ ] `backend/pyproject.toml` — dependencies: fastapi[standard], anthropic, duckdb, sqlglot, pydantic-settings. Dev: pytest, pytest-asyncio, httpx, ruff, mypy
- [ ] `backend/Dockerfile` — Python 3.12-slim, uv install, uvicorn entrypoint
- [ ] `frontend/package.json` — Next.js 14+, TypeScript, Tailwind, Recharts, Zustand, Lucide, clsx, tailwind-merge, cva
- [ ] `frontend/Dockerfile` — Node 18-alpine, npm install, next build + start
- [ ] `docker-compose.yml` — backend (port 8000) + frontend (port 3000) with healthcheck
- [ ] `.env.example` — ANTHROPIC_API_KEY=your-key-here
- [ ] Verify: `docker compose up` starts both services without errors

**Acceptance**:
- [ ] `docker compose up --build` starts both containers
- [ ] `curl http://localhost:8000` returns FastAPI default response
- [ ] `curl http://localhost:3000` returns Next.js page

---

#### Phase 1: Backend Foundation (core infrastructure)

**Goal**: FastAPI project scaffold, DuckDB loaded with data, health endpoint working.

**Tests First (TDD)**:
- [ ] `test_database.py`: DuckDBService loads CSVs correctly, `cursor()` returns valid cursor, row counts match expectations
- [ ] `test_health.py`: GET /health returns 200 with expected schema, returns table names and row counts

**Tasks**:
- [ ] `app/core/config.py` — Settings class with: anthropic_api_key, claude_model, duckdb_data_dir, max_query_retries (default 2), query_timeout_seconds (default 5), max_result_rows (default 1000)
- [ ] `app/core/database.py` — DuckDBService class: singleton connection, `load_csv(table, path)`, `cursor()` context manager, load both CSVs at startup via lifespan
- [ ] `app/main.py` — FastAPI app with lifespan (loads DuckDB), CORS middleware for localhost:3000
- [ ] `app/routers/health.py` — GET /health returns {status, tables_loaded, row_counts}
- [ ] `app/dependencies.py` — get_settings (lru_cache), get_db, get_query_service, get_chat_service
- [ ] Verify data loads correctly: `SELECT COUNT(*) FROM raw_input_metrics` and `SELECT COUNT(*) FROM raw_orders`

**Acceptance**:
- [ ] All Phase 1 tests pass (`uv run pytest tests/test_database.py tests/test_health.py`)
- [ ] `uv run uvicorn app.main:app` starts without errors
- [ ] GET /health returns 200 with table counts
- [ ] DuckDB queries return correct data

---

#### Phase 2: SQL Generation + Validation Pipeline

**Goal**: The core NL→SQL→Results pipeline works end-to-end.

**Tests First (TDD)**:
- [ ] `test_sql_validator.py`: valid SELECT passes, INSERT/UPDATE/DELETE/DROP rejected, multi-statement rejected, invalid table rejected, invalid column rejected, LIMIT enforced if missing, DuckDB extensions blocked
- [ ] `test_query_service.py`: `build_schema_context()` includes DDL + samples + glossary, `execute_query()` returns DataFrame, timeout kills long queries, retry logic feeds error back to LLM
- [ ] `test_llm_provider.py`: LLMProvider Protocol is implemented correctly, ClaudeLLMProvider calls anthropic SDK with correct params

**Tasks**:

- [ ] `app/services/llm_provider.py` — `LLMProvider` Protocol with `generate(system_prompt, messages, tools) -> LLMResponse`. `ClaudeLLMProvider` implementation using anthropic SDK
- [ ] `app/services/query_service.py`:
  - `build_schema_context()` — generates DDL + 3 sample rows + column stats per table + business glossary (metric definitions in Spanish/English)
  - `validate_sql(sql)` — sqlglot parse, reject non-SELECT, reject multi-statement, verify table/column names against allowlist, enforce LIMIT clause
  - `execute_query(sql)` — DuckDB execution with timeout, returns DataFrame
  - `query_with_retry(question, schema_context, messages)` — generates SQL via LLM, validates, executes, retries up to 2x on error feeding error message back to LLM
- [ ] System prompt engineering: role definition, schema injection, few-shot examples for each query type (filtering, comparison, trend, aggregation, multivariable, inference), DuckDB SQL dialect rules, instruction to ask clarifying questions on ambiguity
- [ ] Tool definitions for Claude:
  - `query_database(sql: str)` — validates + executes SQL, returns JSON results
  - `generate_visualization(type, title, data, x_axis, series)` — returns viz config

**SQL validation rules (from SpecFlow analysis)**:
- [ ] Only SELECT statements (reject INSERT, UPDATE, DELETE, DROP, CREATE, COPY, etc.)
- [ ] Single statement only (reject semicolons producing multiple statements)
- [ ] All table references must exist in schema
- [ ] All column references must exist in the referenced table
- [ ] Enforce LIMIT (max 1000 rows, inject if missing)
- [ ] Query execution timeout (5 seconds)
- [ ] Block DuckDB extensions (`load_extension`, `install_extension`)

**Acceptance**:
- [ ] "Top 5 zonas con mayor Lead Penetration esta semana" → correct table result
- [ ] "SELECT * FROM raw_input_metrics; DROP TABLE raw_orders" → rejected by validator
- [ ] Failed SQL → auto-retry with error feedback → correct result on retry

---

#### Phase 3: Chat Service + Session Management

**Goal**: Full conversational flow with memory and context.

**Tests First (TDD)**:
- [ ] `test_session_service.py`: create_session returns valid ID, add_message persists, get_session returns messages in order, sliding window returns only last N turns, summary is generated for older turns
- [ ] `test_chat_service.py`: process_message yields SSE events in correct order, tool calls are dispatched correctly, empty result set returns helpful message, out-of-scope question is handled gracefully

**Tasks**:

- [ ] `app/models/schemas.py`:
  - `ChatRequest(session_id: str | None, message: str)`
  - `ChatResponse(text: str, visualization: VizConfig | None, sql_query: str | None)`
  - `VizConfig(type: Literal["line", "bar", "table"], title: str, x_axis: list[str], series: list[Series])`
  - `Session(id: str, created_at: datetime, messages: list[Message], summary: str | None)`
- [ ] `app/services/session_service.py`:
  - SQLite storage for sessions (create_session, get_session, add_message, list_sessions)
  - Sliding window: return last N complete turns + summary of older turns
  - Summary generation: LLM summarizes older turns when window exceeds threshold (async, after response)
- [ ] `app/services/chat_service.py`:
  - `process_message(session_id, message)` — orchestrates: load session → build context (schema + memory window) → LLM tool loop → save message + response → yield SSE events
  - Tool dispatch: routes `query_database` and `generate_visualization` tool calls to respective services
  - Business context handling: system prompt includes instructions for interpreting domain terms ("zonas problematicas" = deteriorated metrics, "crecimiento" = positive L0W vs L4W trend)
- [ ] `app/routers/chat.py`:
  - `POST /chat/stream` — SSE endpoint, streams: status events, token deltas, tool calls, viz configs, done signal
  - `GET /sessions` — list all sessions (id, created_at, first_message preview)
  - `GET /sessions/{id}` — full session with messages

**Edge cases (from SpecFlow)**:
- [ ] Empty result set → bot explains "No zones matched" + suggests relaxing criteria
- [ ] Out-of-scope question → bot responds "I can help with operational metrics. Try asking about..."
- [ ] Time range outside 9-week window → bot explains data availability
- [ ] Follow-up without clear context → bot asks for clarification
- [ ] Message while streaming → queue and process after current response completes

**Acceptance**:
- [ ] Multi-turn conversation maintains context: "Top zonas en Mexico" → "Y en Brasil?" works correctly
- [ ] Session persists across page refresh
- [ ] Memory window keeps token usage bounded (verify with 20+ turn conversation)

---

#### Phase 4: Visualization Service

**Goal**: Bot returns interactive charts when appropriate.

**Tests First (TDD)**:
- [ ] `test_viz_service.py`: trend question → line type, comparison question → bar type, ranking question → table type, single value → text only, `build_viz_config()` returns valid Recharts-compatible JSON, week labels are mapped correctly (L8W→"Hace 8 sem")

**Tasks**:

- [ ] `app/services/viz_service.py`:
  - `determine_viz_type(question, result_df)` — rules: trend keywords → line, comparison keywords → bar, rankings/lists → table, single value → text only
  - `build_viz_config(type, df, question)` — transforms DataFrame to Recharts-compatible JSON: `{type, title, x_axis, series: [{name, data}]}`
  - Week label mapping: L8W→"Hace 8 sem", L7W→"Hace 7 sem", ..., L0W→"Esta semana"
- [ ] Integrate viz tool into Claude's tool definitions so the LLM can proactively generate charts
- [ ] Add viz config to SSE stream as a dedicated event type

**Acceptance**:
- [ ] "Evolucion de Gross Profit en Chapinero" → line chart with 9 data points
- [ ] "Compara Perfect Order Wealthy vs Non Wealthy en Mexico" → bar chart
- [ ] "Top 5 zonas por Orders" → table (no chart)

---

#### Phase 5: Next.js Frontend

**Goal**: Chat interface with real-time streaming and interactive charts.

**Tasks**:

- [ ] Next.js project setup: App Router, TypeScript, Tailwind CSS, Lucide Icons, Recharts
- [ ] `lib/hooks/useChat.ts` — SSE consumption via fetch + ReadableStream reader (not EventSource, which only supports GET). Handles: token accumulation, tool call indicators, viz config parsing, error states, message queuing
- [ ] `lib/hooks/useSessions.ts` — CRUD against /sessions endpoints
- [ ] Layout components:
  - `Header.tsx` — logo "Rappi Analytics" + session indicator + new session dropdown
  - `Sidebar.tsx` — collapsible, session history list (active highlighted), proactive suggestions section
  - `InputBar.tsx` — pill-shaped input, Send icon button (disabled when empty or streaming), Paperclip icon (disabled, future)
- [ ] Chat components:
  - `WelcomeCard.tsx` — bot avatar, welcome text, 6 suggestion chips covering all query types
  - `MessageBubble.tsx` — user (right-aligned) vs bot (left-aligned), distinct visual styles, avatar icons
  - `TypingIndicator.tsx` — 3-dot animation + pipeline step text ("Analizando...", "Ejecutando query...", "Preparando respuesta...")
- [ ] Visualization components:
  - `DynamicChart.tsx` — switch on viz config type, render appropriate chart component
  - `TrendChart.tsx` — Recharts LineChart with ResponsiveContainer, Tooltip, Legend
  - `ComparisonChart.tsx` — Recharts BarChart
  - `DataTable.tsx` — sortable table with max 10 visible rows + scroll, footer with Copy + Export CSV buttons
- [ ] Responsive: sidebar visible >1024px, drawer on tablet, hidden on mobile
- [ ] Brand: Rappi color palette as CSS variables, Lucide Icons throughout, zero emojis

**Acceptance**:
- [ ] Full conversation flow works end-to-end with streaming
- [ ] Charts render correctly and are interactive (hover tooltip)
- [ ] Session switching preserves history
- [ ] Mobile layout is usable

---

#### Phase 6: Polish + Proactive Suggestions

**Goal**: Proactive analysis suggestions, error UX, data freshness indicator.

**Tasks**:

- [ ] Proactive suggestions in sidebar: on session load, generate 3-4 contextual suggestions based on data anomalies (zones with declining metrics, unusual spikes). Use a lightweight LLM call at session start
- [ ] Error UX: error message bubble with retry button, distinct visual style
- [ ] Data freshness indicator in header: "Datos actualizados al: {date}" derived from CSV load time
- [ ] Suggestion chips after each response: "Profundizar en...", "Comparar con...", "Ver tendencia de..."
- [ ] Export CSV: button on DataTable downloads results as CSV file
- [ ] Loading states: skeleton UI while sessions load, typing indicator during LLM processing

**Acceptance**:
- [ ] Sidebar shows relevant proactive suggestions
- [ ] Error states show retry option
- [ ] CSV export downloads correct data

---

### Testing Strategy (TDD)

Tests are written BEFORE implementation in every phase. The test suite is the specification.

```
tests/
  conftest.py               # Shared fixtures: mock settings, in-memory DuckDB, mock LLM
  test_database.py          # DuckDB loading, cursor management
  test_health.py            # Health endpoint schema
  test_llm_provider.py      # Protocol compliance, Claude SDK integration
  test_query_service.py     # SQL generation, execution, retry logic
  test_sql_validator.py     # Security: injection, multi-statement, dangerous functions
  test_chat_service.py      # Tool loop orchestration, response formatting
  test_session_service.py   # CRUD, sliding window, summary generation
  test_viz_service.py       # Chart type detection, config generation
  test_routers.py           # Integration: SSE streaming, session endpoints
```

**Key testing patterns**:
- **TDD cycle**: Red (write failing test) → Green (minimum implementation) → Refactor
- Real in-memory DuckDB for integration tests (fast, disposable)
- `app.dependency_overrides` to swap services in router tests
- Mock Anthropic client at service boundary (not SDK internals)
- Dedicated security test suite for SQL injection vectors
- Each phase's "Tests First" section defines what to write before coding

---

## Acceptance Criteria

### Functional Requirements
- [ ] Filtering queries return correct ranked/filtered results
- [ ] Comparison queries return side-by-side data with bar chart
- [ ] Trend queries return time series with line chart
- [ ] Aggregation queries return grouped summaries
- [ ] Multivariable queries correctly cross-reference metrics
- [ ] Inference queries provide analysis with supporting data
- [ ] Business context understood ("zonas problematicas" = deteriorated metrics)
- [ ] Follow-up questions use conversation context
- [ ] Proactive suggestions appear in sidebar
- [ ] Conversational memory persists across turns

### Non-Functional Requirements
- [ ] SQL injection attempts are blocked (sqlglot validation)
- [ ] Query timeout enforced (5s)
- [ ] Result row limit enforced (1000)
- [ ] SSE streaming delivers tokens progressively
- [ ] Responsive layout works on desktop/tablet/mobile
- [ ] No emojis in UI — Lucide Icons only

### Quality Gates
- [ ] All tests pass (`uv run pytest`)
- [ ] No ruff lint errors (`uv run ruff check`)
- [ ] Type checking passes (`uv run mypy app/`)
- [ ] Code follows layered architecture (no business logic in routers)

## Scoping Decisions for Interview Context

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Authentication | None (skip) | Out of scope for technical case. Mention "would add OAuth/SSO" if asked. |
| Data refresh | Manual restart | CSVs are static for the evaluation. Mention "scheduled ETL" if asked. |
| Concurrency | Single instance, cursor-per-request | Sufficient for demo. Mention "connection pool + horizontal scaling" if asked. |
| Session cleanup | No expiration | Demo scope. Mention "TTL + cron cleanup" if asked. |
| Language | Bot responds in user's language (Spanish/Portuguese/English) | Claude handles this natively via system prompt instruction. |
| PDF export | Skip | Low value for evaluation. CSV export is sufficient as bonus. |

## Dependencies & Prerequisites

- Python 3.12+
- Node.js 18+
- Docker + Docker Compose (for containerized deployment)
- Anthropic API key (ANTHROPIC_API_KEY env var)
- uv package manager (for local development)
- The 2 CSV data files (already in /data)
- Figma design: https://www.figma.com/make/Y8jxLwGDPSoVPUoM19ID2n/Rappi-Operations-Analytics-Chatbot

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM generates wrong SQL | Medium | High | sqlglot validation + retry loop + few-shot examples in prompt |
| DuckDB query hangs | Low | High | 5s timeout on all queries |
| Claude API rate limit | Low | Medium | Graceful error message + retry suggestion |
| Metric name mismatch (user types alias) | Medium | Medium | Business glossary in system prompt with aliases |
| SSE connection drops mid-stream | Low | Low | Frontend shows partial response + retry option |

## References

### Libraries & Versions
- FastAPI >= 0.135.0 (native SSE via EventSourceResponse)
- anthropic (latest) — tool_runner under client.beta namespace
- duckdb >= 1.0.0 — cursor() shares connection lock
- sqlglot (latest) — parse with dialect="duckdb"
- pydantic-settings >= 2.7.0
- Recharts ^3.3.0 — built-in responsive
- Next.js >= 14.0.0 — App Router with Web Request/Response

### Key Implementation Notes
- DuckDB `cursor()` creates handles on the same connection (serialized, not parallel). Fine for this scope.
- sqlglot is a parser, not a full validator. Combine with allowlist-based table/column checks.
- Claude `tool_runner` is under `client.beta.messages.tool_runner()`, not client.messages.
- `EventSource` browser API only supports GET. Use `fetch()` + ReadableStream for POST-based SSE.
- Recharts components require `"use client"` directive.
- `CORS allow_origins=["*"]` is incompatible with `allow_credentials=True`. List specific origins.

### Research Sources
- tiangolo/full-stack-fastapi-template — project structure reference
- zhanymkanov/fastapi-best-practices — Netflix Dispatch-inspired patterns
- DuckDB concurrency docs + GitHub discussion #13719
- Anthropic SDK tools.md — @beta_tool and tool_runner patterns
- sqlglot GitHub — AST traversal with exp.Table, exp.Column, exp.Select
