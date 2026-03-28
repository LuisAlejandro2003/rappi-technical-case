"""LLM provider abstraction with Claude implementation."""

from typing import Any, Protocol

import anthropic


class LLMResponse:
    def __init__(
        self,
        content: str,
        tool_calls: list[dict] | None = None,
        stop_reason: str = "end_turn",
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.stop_reason = stop_reason


class LLMProvider(Protocol):
    def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse: ...


class ClaudeLLMProvider:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        content = ""
        tool_calls: list[dict] = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
        )
