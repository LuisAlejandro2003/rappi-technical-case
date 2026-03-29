from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class Series(BaseModel):
    name: str
    data: list[float | int | None]


class VizConfig(BaseModel):
    type: Literal["line", "bar", "table"]
    title: str
    x_axis: list[str] = []
    series: list[Series] = []
    raw_data: list[dict] | None = None


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sql_query: str | None = None
    visualization: VizConfig | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Session(BaseModel):
    id: str
    created_at: datetime
    messages: list[Message] = []
    summary: str | None = None
    title: str | None = None


class SSEEvent(BaseModel):
    event: str  # "status", "token", "tool_call", "visualization", "done", "error"
    data: dict | str


# --- Insights System ---

class Insight(BaseModel):
    id: str
    category: Literal["anomalias", "tendencias", "benchmarking", "correlaciones", "oportunidades"]
    severity: float
    title: str
    description: str
    zone: str | None = None
    city: str | None = None
    country: str | None = None
    metrics: list[str]
    magnitude: float
    direction: Literal["improvement", "deterioration", "neutral"]
    recommendation: str = ""
    explore_query: str = ""


class InsightReport(BaseModel):
    id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    executive_summary: str = ""
    findings: list[Insight] = []
    category_counts: dict[str, int] = {}
    markdown_report: str = ""
    # Narrative sections parsed from LLM markdown
    narrative_sections: dict[str, str] = {}  # e.g. {"anomalias": "...", "tendencias": "..."}
