"""Tests for ChatService."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.schemas import SSEEvent
from app.services.chat_service import ChatService, TOOLS
from app.services.llm_provider import LLMResponse
from app.services.query_service import QueryService
from app.services.session_service import SessionService


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        duckdb_data_dir="/tmp/fake",
    )


@pytest.fixture()
def session_service() -> SessionService:
    return SessionService(db_path=":memory:")


@pytest.fixture()
def mock_llm():
    return MagicMock()


@pytest.fixture()
def mock_query_service():
    qs = MagicMock(spec=QueryService)
    qs.get_schema_context.return_value = "CREATE TABLE test (id INT);"
    return qs


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


async def _collect_events(async_gen) -> list[SSEEvent]:
    events = []
    async for event in async_gen:
        events.append(event)
    return events


class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_yields_sse_events(self, chat_service: ChatService, mock_llm):
        mock_llm.generate.return_value = LLMResponse(
            content="Hello!", tool_calls=[], stop_reason="end_turn"
        )
        events = await _collect_events(
            chat_service.process_message(None, "Hi there")
        )

        event_types = [e.event for e in events]
        assert "session" in event_types
        assert "status" in event_types
        assert "token" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_creates_session_if_none(self, chat_service: ChatService, mock_llm):
        mock_llm.generate.return_value = LLMResponse(
            content="Hello!", tool_calls=[], stop_reason="end_turn"
        )
        events = await _collect_events(
            chat_service.process_message(None, "Hi")
        )

        session_events = [e for e in events if e.event == "session"]
        assert len(session_events) == 1
        session_id = session_events[0].data["session_id"]
        assert session_id is not None

        # Verify session was created in session_service
        session = chat_service.session_service.get_session(session_id)
        assert session is not None

    @pytest.mark.asyncio
    async def test_handles_tool_call(
        self, chat_service: ChatService, mock_llm, mock_query_service
    ):
        # First call: LLM returns a tool_use
        tool_response = LLMResponse(
            content="Let me query that.",
            tool_calls=[
                {
                    "id": "tool_1",
                    "name": "query_database",
                    "input": {"sql": "SELECT 1"},
                }
            ],
            stop_reason="tool_use",
        )
        # Second call: LLM returns final text
        final_response = LLMResponse(
            content="Here are the results.", tool_calls=[], stop_reason="end_turn"
        )
        mock_llm.generate.side_effect = [tool_response, final_response]
        mock_query_service.validate_and_execute.return_value = [{"col": 1}]

        events = await _collect_events(
            chat_service.process_message(None, "Show me data")
        )

        event_types = [e.event for e in events]
        assert "tool_call" in event_types
        mock_query_service.validate_and_execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_handles_tool_call_loop(
        self, chat_service: ChatService, mock_llm, mock_query_service
    ):
        # First call: tool_use
        first = LLMResponse(
            content="Querying...",
            tool_calls=[
                {"id": "t1", "name": "query_database", "input": {"sql": "SELECT 1"}}
            ],
            stop_reason="tool_use",
        )
        # Second call: another tool_use
        second = LLMResponse(
            content="One more query...",
            tool_calls=[
                {"id": "t2", "name": "query_database", "input": {"sql": "SELECT 2"}}
            ],
            stop_reason="tool_use",
        )
        # Third call: end_turn
        third = LLMResponse(
            content="Done!", tool_calls=[], stop_reason="end_turn"
        )
        mock_llm.generate.side_effect = [first, second, third]
        mock_query_service.validate_and_execute.return_value = [{"x": 1}]

        events = await _collect_events(
            chat_service.process_message(None, "Complex query")
        )

        assert mock_llm.generate.call_count == 3
        tool_events = [e for e in events if e.event == "tool_call"]
        assert len(tool_events) == 2

    @pytest.mark.asyncio
    async def test_returns_error_event_on_llm_failure(
        self, chat_service: ChatService, mock_llm
    ):
        mock_llm.generate.side_effect = Exception("API error")

        events = await _collect_events(
            chat_service.process_message(None, "Hi")
        )

        error_events = [e for e in events if e.event == "error"]
        assert len(error_events) == 1
        assert "API error" in error_events[0].data["message"]

    @pytest.mark.asyncio
    async def test_returns_helpful_message_on_empty_results(
        self, chat_service: ChatService, mock_llm, mock_query_service
    ):
        tool_response = LLMResponse(
            content="Let me check.",
            tool_calls=[
                {"id": "t1", "name": "query_database", "input": {"sql": "SELECT 1 WHERE 0=1"}}
            ],
            stop_reason="tool_use",
        )
        final_response = LLMResponse(
            content="No data found.", tool_calls=[], stop_reason="end_turn"
        )
        mock_llm.generate.side_effect = [tool_response, final_response]
        mock_query_service.validate_and_execute.return_value = []

        events = await _collect_events(
            chat_service.process_message(None, "Show empty data")
        )

        # The tool dispatch should return a helpful message for empty results
        # This is verified by checking the LLM received the empty-result message
        # in the tool_result content passed back
        assert mock_llm.generate.call_count == 2
        second_call_messages = mock_llm.generate.call_args_list[1][0][1]
        tool_result_msg = second_call_messages[-1]
        tool_result_content = json.loads(tool_result_msg["content"][0]["content"])
        assert "message" in tool_result_content
        assert "no retorno resultados" in tool_result_content["message"].lower()


class TestBuildSystemPrompt:
    def test_includes_schema_context(
        self, chat_service: ChatService, mock_query_service
    ):
        prompt = chat_service.build_system_prompt()
        assert "CREATE TABLE test (id INT);" in prompt
        mock_query_service.get_schema_context.assert_called_once()


class TestBuildTools:
    def test_returns_correct_tool_definitions(self, chat_service: ChatService):
        tools = chat_service.build_tools()
        assert len(tools) == 2
        tool_names = {t["name"] for t in tools}
        assert "query_database" in tool_names
        assert "generate_visualization" in tool_names
