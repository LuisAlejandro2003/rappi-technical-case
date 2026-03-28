import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.dependencies import get_chat_service, get_session_service

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
