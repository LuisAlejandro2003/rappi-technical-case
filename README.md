# Rappi Operations Analytics Chatbot

Sistema de analisis inteligente para operaciones Rappi. Dos modulos integrados:

1. **Bot Conversacional** — Consultas en lenguaje natural traducidas a SQL contra datos operacionales
2. **Insights Automaticos** — Deteccion automatica de anomalias, tendencias, benchmarking, correlaciones y oportunidades con reporte ejecutivo generado por IA

## Quick Start

```bash
# 1. Configurar API key
cp .env.example .env
# Editar .env y agregar ANTHROPIC_API_KEY

# 2. Backend
cd backend
pip install -r requirements.txt   # o: uv sync
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health

## Arquitectura

```
                         ┌─────────────────────────────────────────┐
                         │           Frontend (Next.js 14)          │
                         │                                         │
                         │  ┌─────────────┐   ┌─────────────────┐  │
                         │  │  Chat Tab   │   │  Insights Tab   │  │
                         │  │  (SSE)      │   │  (SSE)          │  │
                         │  └──────┬──────┘   └───────┬─────────┘  │
                         └─────────┼──────────────────┼────────────┘
                                   │                  │
                    POST /chat/stream         POST /insights/generate
                                   │                  │
                         ┌─────────┼──────────────────┼────────────┐
                         │         ▼                  ▼            │
                         │  ┌─────────────┐   ┌─────────────────┐  │
                         │  │ ChatService │   │InsightsService  │  │
                         │  │ (tool loop) │   │(5 SQL detectors │  │
                         │  │             │   │ + LLM narrative)│  │
                         │  └──────┬──────┘   └───────┬─────────┘  │
                         │         │                  │            │
                         │         ▼                  ▼            │
                         │  ┌─────────────────────────────────┐    │
                         │  │   DuckDB (in-memory, CSV-based)  │    │
                         │  │   3 tablas operacionales          │    │
                         │  └─────────────────────────────────┘    │
                         │           Backend (FastAPI)              │
                         └─────────────────────────────────────────┘
```

### Stack

| Capa | Tecnologia | Justificacion |
|------|-----------|---------------|
| Backend | FastAPI + Python 3.12 | Async nativo, tipado, ecosystem AI |
| Base de datos | DuckDB (in-memory) | OLAP columnar, 10-100x mas rapido que SQLite para agregaciones |
| LLM | Claude via Anthropic SDK | Tool use nativo, sin LangChain |
| Frontend | Next.js 14 + Tailwind + Recharts | App Router, SSE streaming, visualizaciones |
| State | Zustand | Ligero, sin boilerplate |

## Decisiones Tecnicas

### DT-001: LLM como traductor, no calculadora

El LLM traduce lenguaje natural a SQL. **Nunca calcula sobre datos crudos.** Si el usuario pregunta "promedio de Perfect Orders en Mexico", el LLM genera `SELECT AVG(L0W_ROLL) FROM raw_input_metrics WHERE COUNTRY='MX' AND METRIC='Perfect Orders'` — no intenta sumar valores en su contexto.

**Por que**: El LLM no es calculadora (puede sumar mal o ignorar NULL). No escala (millones de filas no caben en context window). SQL es verificable, reproducible y auditable.

### DT-002: DuckDB sobre PostgreSQL/SQLite

DuckDB es un motor OLAP columnar in-memory. Para queries analiticas (GROUP BY, MEDIAN, ventanas temporales) es 10-100x mas rapido que SQLite y no requiere servidor como PostgreSQL.

**Por que**: Los datos son CSVs estaticos cargados en memoria. No hay escrituras transaccionales (no necesitamos ACID). Las queries son 100% analiticas. DuckDB soporta funciones como `MEDIAN()`, `CORR()`, `read_csv_auto()` que simplifican el pipeline.

### DT-003: SDK directo sin LangChain

Usamos el Anthropic SDK directamente con un `LLMProvider` Protocol para abstraccion. No usamos LangChain.

**Por que**: LangChain agrega overhead de abstraccion (chains, agents, parsers) que ocultan el flujo de control y dificultan el debugging. Con el SDK directo, el tool loop es transparente — vemos exactamente que mensajes recibe el LLM, que tools invoca, y que resultados obtiene. Ademas, el `LLMProvider` Protocol permite hacer swap a otro proveedor (GPT-4, Gemini) con una sola implementacion.

### DT-004: Pipeline hibrido para Insights (SQL + LLM)

La deteccion de insights es SQL deterministico (5 detectores). El LLM solo genera la narrativa del reporte ejecutivo a partir de hallazgos ya estructurados.

**Por que**: "Vichayito tiene Gross Profit UE de -$97.13 vs mediana -$0.50" es un calculo exacto — no deberia depender del LLM. La IA agrega valor donde es irremplazable: interpretar los datos en contexto de negocio y generar recomendaciones accionables. Precision donde se necesita, inteligencia donde aporta.

## Modulo 1: Bot Conversacional

### Flujo

```
Usuario escribe pregunta
    → LLM genera SQL (tool: query_database)
    → sqlglot valida AST (solo SELECT, tablas permitidas)
    → DuckDB ejecuta
    → LLM genera visualizacion si aplica (tool: generate_visualization)
    → LLM analiza resultados y responde con markdown
    → Frontend renderiza texto + chart/tabla
```

### Capacidades

- **Filtrado**: "Top 5 zonas con mayor Lead Penetration esta semana"
- **Comparaciones**: "Compara Perfect Orders entre zonas Wealthy y Non Wealthy en Mexico"
- **Tendencias temporales**: "Evolucion de Gross Profit UE en Chapinero ultimas 8 semanas"
- **Agregaciones**: "Promedio de Lead Penetration por pais"
- **Analisis multivariable**: "Zonas con alto Lead Penetration pero bajo Perfect Order"
- **Inferencia**: "Zonas que mas crecen en ordenes y que podria explicar el crecimiento"

### Contexto de Negocio

El LLM recibe contexto operacional a traves de tres capas:

1. **Business Glossary** (`business_context.j2`) — Mapeo de terminos de negocio a SQL (ej: "zonas problematicas" = metricas deterioradas)
2. **Few-Shot SQL** — 5 ejemplos representativos de NL→SQL
3. **Data Profiler** (`data_profiler.py`) — Perfil estadistico generado al startup: promedios por pais, tendencias, zonas outlier, volumen de ordenes

## Modulo 2: Insights Automaticos

### Pipeline

```
Click "Generar Reporte"
    → 5 detectores SQL ejecutan en secuencia
    → Severity scoring + dedup + diversidad de metricas
    → Top 12-15 hallazgos estructurados
    → LLM genera reporte narrativo en markdown
    → Frontend renderiza: summary cards + resumen ejecutivo + categorias con cards
```

### Categorias de Deteccion

| Categoria | Que detecta | Ejemplo |
|-----------|-------------|---------|
| Anomalias | Cambios >25% semana a semana | "GP UE paso de $0.00 a -$1.69 en GRAN_MENDOZA_GODOY" |
| Tendencias | 3+ semanas consecutivas de deterioro | "GP UE lleva 5 semanas cayendo en Santo_Domingo" |
| Benchmarking | Zonas >40% debajo de mediana de pares | "Vichayito: -$97.13 vs mediana -$0.50" |
| Correlaciones | Metricas relacionadas ambas debiles | "Lead Penetration y Funnel CVR bajas en CiudadManteOps1" |
| Oportunidades | Mejoras sostenidas o debilidades focalizadas | "GP UE mejora 5 semanas en GO-GYN-Centro (+$3.12)" |

### Integracion Chat ↔ Insights

Cada hallazgo tiene un boton "Explorar en chat" que abre el chatbot con una pregunta pre-construida para profundizar. El resumen de insights se inyecta en el system prompt del chat para que el LLM tenga contexto de los hallazgos mas recientes.

### Calibracion

- Valores en dolares se muestran como `$X.XX`, ratios como `X.X%`, cambios en puntos porcentuales (`pp`)
- Magnitudes extremas se capean (SEVERITY_MAGNITUDE_CAP = 5.0) para evitar que outliers dominen
- Maximo 2 hallazgos por metrica por categoria para forzar diversidad
- El LLM narrativo tiene restricciones explicitas: no inventar datos, no recalcular numeros, hipotesis como hipotesis

## Estructura del Proyecto

```
backend/
  app/
    core/           # Settings, DuckDB service
    models/         # Pydantic schemas (Message, Insight, InsightReport)
    services/       # ChatService, InsightsService, QueryService, DataProfiler, LLMProvider
    templates/      # Jinja2: system_prompt, business_context, response_rules, insights_prompt
    routers/        # /chat (stream, sessions, suggestions) + /insights (generate, report)
  tests/            # 120+ tests (pytest)
frontend/
  src/
    app/            # Next.js App Router
    components/     # Layout (header, sidebar, input-bar)
    features/
      chat/         # MessageBubble, MarkdownRenderer, useChatStream
      insights/     # InsightsView, InsightsReport, InsightsLoading, InsightsEmpty
      visualization/# LineChart, BarChart, DataTable, ChartContainer
    stores/         # Zustand (chat-store, session-store, insights-store)
    lib/            # API client, viz-utils
data/               # CSV operacionales (RAW_INPUT_METRICS, RAW_ORDERS, RAW_SUMMARY)
docs/
  brainstorms/      # Documentos de diseno
  plans/            # Planes de implementacion
```

## Tests

```bash
cd backend
pytest tests/ -v
# 120+ tests: database, query validation, chat service, insights detectors, SQL injection prevention
```
