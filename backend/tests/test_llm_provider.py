"""Tests for LLM provider abstraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_provider import ClaudeLLMProvider, LLMProvider, LLMResponse


class TestLLMResponse:
    def test_default_values(self):
        resp = LLMResponse(content="hello")
        assert resp.content == "hello"
        assert resp.tool_calls == []
        assert resp.stop_reason == "end_turn"

    def test_with_tool_calls(self):
        calls = [{"id": "1", "name": "fn", "input": {}}]
        resp = LLMResponse(content="", tool_calls=calls, stop_reason="tool_use")
        assert len(resp.tool_calls) == 1
        assert resp.stop_reason == "tool_use"


class TestLLMProviderProtocol:
    def test_protocol_defines_generate(self):
        """LLMProvider should be a Protocol with generate() method."""
        assert hasattr(LLMProvider, "generate")

    def test_claude_provider_satisfies_protocol(self):
        """ClaudeLLMProvider should be structurally compatible with LLMProvider."""
        # Check that ClaudeLLMProvider has the generate method
        assert hasattr(ClaudeLLMProvider, "generate")


class TestClaudeLLMProvider:
    @patch("app.services.llm_provider.anthropic")
    def test_init_creates_client(self, mock_anthropic):
        provider = ClaudeLLMProvider(api_key="test-key", model="claude-test")
        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")
        assert provider.model == "claude-test"

    @patch("app.services.llm_provider.anthropic")
    def test_generate_calls_client_correctly(self, mock_anthropic):
        # Set up mock response
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Hello, world!"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        provider = ClaudeLLMProvider(api_key="test-key", model="claude-test")
        result = provider.generate(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )

        mock_client.messages.create.assert_called_once_with(
            model="claude-test",
            max_tokens=4096,
            system="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result.content == "Hello, world!"
        assert result.tool_calls == []
        assert result.stop_reason == "end_turn"

    @patch("app.services.llm_provider.anthropic")
    def test_generate_with_tools(self, mock_anthropic):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Let me query that."

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "call_123"
        mock_tool_block.name = "run_sql"
        mock_tool_block.input = {"query": "SELECT 1"}

        mock_response = MagicMock()
        mock_response.content = [mock_text_block, mock_tool_block]
        mock_response.stop_reason = "tool_use"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        provider = ClaudeLLMProvider(api_key="test-key", model="claude-test")
        tools = [{"name": "run_sql", "description": "Run SQL", "input_schema": {}}]
        result = provider.generate(
            system_prompt="System",
            messages=[{"role": "user", "content": "Query"}],
            tools=tools,
        )

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs.get("tools") == tools or (
            len(call_kwargs.args) == 0 and "tools" in call_kwargs.kwargs
        )
        assert result.content == "Let me query that."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "run_sql"
        assert result.tool_calls[0]["input"] == {"query": "SELECT 1"}
        assert result.stop_reason == "tool_use"

    @patch("app.services.llm_provider.anthropic")
    def test_generate_without_tools_omits_tools_kwarg(self, mock_anthropic):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "response"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        provider = ClaudeLLMProvider(api_key="test-key", model="claude-test")
        provider.generate(
            system_prompt="System",
            messages=[{"role": "user", "content": "Hi"}],
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs
