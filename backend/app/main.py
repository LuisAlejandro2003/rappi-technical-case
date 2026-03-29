from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_db
from app.routers import chat, health, insights


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: eagerly initialize DuckDB so failures surface early
    get_db()
    yield


app = FastAPI(
    title="Rappi Analytics API",
    description="NL-to-SQL analytics chatbot for Rappi operations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(insights.router)
