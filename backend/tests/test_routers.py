"""Tests for chat and session routers."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_chat_service, get_session_service
from app.main import app
from app.models.schemas import Message, SSEEvent
from app.services.chat_service import ChatService
from app.services.llm_provider import LLMResponse
from app.services.query_service import QueryService
from app.services.session_service import SessionService


@pytest.fixture()
def session_service() -> SessionService:
    return SessionService(db_path=":memory:")


@pytest.fixture()
def mock_llm():
    llm = MagicMock()
    llm.generate.return_value = LLMResponse(
        content="Test response", tool_calls=[], stop_reason="end_turn"
    )
    return llm


@pytest.fixture()
def mock_query_service():
    qs = MagicMock(spec=QueryService)
    qs.get_schema_context.return_value = "schema"
    return qs


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(anthropic_api_key="test-key", duckdb_data_dir="/tmp/fake")


@pytest.fixture()
def chat_service(
    mock_llm, mock_query_service, session_service, mock_settings
) -> ChatService:
    return ChatService(
        llm=mock_llm,
        query_service=mock_query_service,
        session_service=session_service,
        settings=mock_settings,
    )


@pytest.fixture()
def client(chat_service: ChatService, session_service: SessionService) -> TestClient:
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_session_service] = lambda: session_service
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


class TestChatStream:
    def test_returns_sse_response(self, client: TestClient):
        response = client.post(
            "/chat/stream",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE events from body
        body = response.text
        assert "event: session" in body or "event:session" in body
        assert "event: done" in body or "event:done" in body


class TestSessions:
    def test_list_sessions(self, client: TestClient, session_service: SessionService):
        session_service.create_session()
        session_service.create_session()

        response = client.get("/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2

    def test_get_session_with_messages(
        self, client: TestClient, session_service: SessionService
    ):
        sid = session_service.create_session()
        session_service.add_message(sid, Message(role="user", content="Hi"))
        session_service.add_message(sid, Message(role="assistant", content="Hello!"))

        response = client.get(f"/chat/sessions/{sid}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sid
        assert len(data["messages"]) == 2

    def test_get_session_404_for_unknown(self, client: TestClient):
        response = client.get("/sessions/nonexistent-id")
        assert response.status_code == 404
