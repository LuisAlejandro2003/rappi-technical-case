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

## Project Structure

```
backend/
  app/
    core/       # Config, database, prompts
    models/     # Pydantic schemas
    services/   # Business logic (Claude, DuckDB, query pipeline)
    routers/    # API endpoints
    main.py     # FastAPI application
  tests/
frontend/
  src/app/      # Next.js app router pages
data/           # CSV data files
docs/           # Project documentation
```
