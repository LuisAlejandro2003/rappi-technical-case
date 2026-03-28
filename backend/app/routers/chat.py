import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.core.database import DuckDBService
from app.dependencies import get_chat_service, get_session_service, get_db

router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)):
    async def event_generator():
        async for event in chat_service.process_message(request.session_id, request.message):
            data = event.data if isinstance(event.data, str) else json.dumps(event.data)
            yield {"event": event.event, "data": data}

    return EventSourceResponse(event_generator())


@router.get("/sessions")
async def list_sessions(session_service: SessionService = Depends(get_session_service)):
    return session_service.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, session_service: SessionService = Depends(get_session_service)):
    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/suggestions")
async def get_suggestions(db: DuckDBService = Depends(get_db)):
    """Generate proactive analysis suggestions based on data patterns."""
    suggestions = []

    try:
        # Find zones with biggest L0W vs L4W decline in orders
        decline_query = """
            SELECT ZONE, CITY, COUNTRY,
                   L0W - L4W as decline,
                   L0W, L4W
            FROM raw_orders
            WHERE L0W < L4W
            ORDER BY decline ASC
            LIMIT 1
        """
        decline = db.execute(decline_query)
        if decline:
            zone = decline[0]
            suggestions.append({
                "id": "sug-decline",
                "text": f"Ordenes cayeron en {zone['ZONE']} ({zone['CITY']}, {zone['COUNTRY']}): {zone['L0W']:,.0f} vs {zone['L4W']:,.0f} hace 4 semanas",
                "category": "Alerta",
            })

        # Find metric with biggest improvement
        improvement_query = """
            SELECT METRIC, COUNTRY,
                   AVG(L0W_ROLL) as current_avg,
                   AVG(L4W_ROLL) as past_avg,
                   AVG(L0W_ROLL) - AVG(L4W_ROLL) as improvement
            FROM raw_input_metrics
            GROUP BY METRIC, COUNTRY
            HAVING improvement > 0
            ORDER BY improvement DESC
            LIMIT 1
        """
        improvement = db.execute(improvement_query)
        if improvement:
            m = improvement[0]
            suggestions.append({
                "id": "sug-improve",
                "text": f"{m['METRIC']} mejoro en {m['COUNTRY']}: +{m['improvement']:.2%} vs hace 4 semanas",
                "category": "Tendencia",
            })

        # Suggest a comparison
        suggestions.append({
            "id": "sug-compare",
            "text": "Comparar Perfect Orders entre zonas Wealthy vs Non Wealthy",
            "category": "Sugerencia",
        })

        # Suggest trend analysis
        suggestions.append({
            "id": "sug-trend",
            "text": "Ver tendencia de Gross Profit por pais en las ultimas 8 semanas",
            "category": "Analisis",
        })

    except Exception:
        # Fallback static suggestions
        suggestions = [
            {"id": "sug-1", "text": "Top 5 zonas con mayor volumen de ordenes", "category": "Sugerencia"},
            {"id": "sug-2", "text": "Tendencia de Perfect Orders esta semana", "category": "Analisis"},
            {"id": "sug-3", "text": "Zonas con metricas en deterioro", "category": "Alerta"},
        ]

    return suggestions


@router.get("/data-freshness")
async def data_freshness(db: DuckDBService = Depends(get_db)):
    """Return data freshness information."""
    row_counts = db.get_row_counts()
    return {
        "last_updated": "Datos de las ultimas 9 semanas (L8W a L0W)",
        "tables": row_counts,
    }
