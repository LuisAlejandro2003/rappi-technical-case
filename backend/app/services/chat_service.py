import json
import logging
import re
from pathlib import Path
from typing import AsyncGenerator

from jinja2 import Environment, FileSystemLoader

from app.core.config import Settings

logger = logging.getLogger(__name__)
from app.services.llm_provider import LLMProvider, LLMResponse
from app.services.query_service import QueryService
from app.services.session_service import SessionService
from app.services.data_profiler import DataProfiler
from app.models.schemas import Message, VizConfig, SSEEvent

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    keep_trailing_newline=True,
)

_SUGGESTIONS_DELIMITER = "---SUGERENCIAS---"
_SUGGESTION_PATTERN = re.compile(r"^\s*[-\u2022]\s*(.+)$", re.MULTILINE)
_MAX_SUGGESTIONS = 3


def _extract_suggestions(text: str) -> tuple[str, list[str]]:
    """Extract follow-up suggestions from LLM response text.

    Splits on the LAST occurrence of the suggestions delimiter, parses bullet
    points after it, and returns (clean_text, suggestions_list).  Designed to
    never raise on malformed input.
    """
    if not text:
        return ("", [])

    idx = text.rfind(_SUGGESTIONS_DELIMITER)
    if idx == -1:
        return (text, [])

    clean_text = text[:idx].rstrip()
    suggestions_block = text[idx + len(_SUGGESTIONS_DELIMITER) :]

    matches = _SUGGESTION_PATTERN.findall(suggestions_block)
    suggestions = [s.strip() for s in matches if s.strip()]

    return (clean_text, suggestions[:_MAX_SUGGESTIONS])


TOOLS = [
    {
        "name": "query_database",
        "description": "Execute a SQL query against the Rappi operations database. Use this to retrieve data for answering user questions. Write DuckDB-compatible SQL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SQL SELECT query to execute."
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "generate_visualization",
        "description": "Generate a chart visualization for the data. Use for time series (line), comparisons (bar), or detailed data (table).",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["line", "bar", "table"],
                    "description": "Chart type: line for trends, bar for comparisons, table for detailed data."
                },
                "title": {
                    "type": "string",
                    "description": "Chart title."
                },
                "x_axis": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels for the X axis."
                },
                "series": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "data": {"type": "array", "items": {"type": "number"}}
                        },
                        "required": ["name", "data"]
                    },
                    "description": "Data series for the chart."
                },
                "raw_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Raw data rows for table type."
                }
            },
            "required": ["type", "title"]
        }
    }
]


class ChatService:
    def __init__(
        self,
        llm: LLMProvider,
        query_service: QueryService,
        session_service: SessionService,
        settings: Settings,
        data_profiler: DataProfiler | None = None,
    ):
        self.llm = llm
        self.query_service = query_service
        self.session_service = session_service
        self.settings = settings
        self.data_profiler = data_profiler
        self._insights_summary_fn = None  # callable that returns str | None
        self._system_prompt: str | None = None
        self._last_insights_summary: str | None = None

    def build_system_prompt(self, insights_summary: str | None = None) -> str:
        if self._system_prompt is None or insights_summary != self._last_insights_summary:
            schema_ctx = self.query_service.get_schema_context()
            data_profile = ""
            if self.data_profiler:
                try:
                    data_profile = self.data_profiler.build_profile()
                except Exception as e:
                    logger.warning("Failed to build data profile: %s", e)
                    data_profile = ""
            template = _jinja_env.get_template("system_prompt.j2")
            self._system_prompt = template.render(
                schema_context=schema_ctx,
                data_profile=data_profile,
                insights_summary=insights_summary or "",
            )
            self._last_insights_summary = insights_summary
        return self._system_prompt

    def build_tools(self) -> list[dict]:
        return TOOLS

    async def process_message(
        self, session_id: str | None, user_message: str
    ) -> AsyncGenerator[SSEEvent, None]:
        # Create or get session
        if session_id is None:
            session_id = self.session_service.create_session()
        else:
            self.session_service.ensure_session_exists(session_id)

        # Save user message
        self.session_service.add_message(
            session_id,
            Message(role="user", content=user_message),
        )

        yield SSEEvent(event="session", data={"session_id": session_id})
        yield SSEEvent(event="status", data={"message": "Analizando tu pregunta..."})

        # Build conversation context
        messages_window = self.session_service.get_messages_window(session_id)
        api_messages = [
            {"role": m.role, "content": m.content} for m in messages_window
        ]

        insights_summary = self._insights_summary_fn() if self._insights_summary_fn else None
        system_prompt = self.build_system_prompt(insights_summary=insights_summary)
        tools = self.build_tools()

        try:
            # Tool loop
            max_iterations = 5
            assistant_text = ""
            streamed = False
            viz_config = None
            sql_query = None

            for _ in range(max_iterations):
                response = self.llm.generate(system_prompt, api_messages, tools)

                has_tool_calls = response.tool_calls and response.stop_reason != "end_turn"

                if response.content:
                    assistant_text += response.content

                if has_tool_calls:
                    # Intermediate iteration: text goes to assistant_text for
                    # conversation context but is NOT shown to the user.
                    pass
                else:
                    # Final response: only stream THIS iteration's text
                    if response.content:
                        clean_text, suggestions = _extract_suggestions(response.content)
                        yield SSEEvent(event="token", data={"text": clean_text})
                        if suggestions:
                            yield SSEEvent(event="follow_up_suggestions", data={"suggestions": suggestions})
                        # Persist only the clean final text, not intermediate thinking
                        assistant_text = clean_text
                        streamed = True
                    break

                # Process tool calls
                for tool_call in response.tool_calls:
                    yield SSEEvent(
                        event="tool_call",
                        data={"tool": tool_call["name"], "input": tool_call["input"]},
                    )

                    tool_result = self._dispatch_tool(tool_call)

                    if tool_call["name"] == "query_database" and "error" not in tool_result:
                        sql_query = tool_call["input"].get("sql")
                        yield SSEEvent(event="status", data={"message": "Ejecutando query..."})
                    elif tool_call["name"] == "generate_visualization" and "error" not in tool_result:
                        viz_config = VizConfig(**tool_call["input"])
                        yield SSEEvent(event="visualization", data=viz_config.model_dump())

                    # Add assistant message with tool use and tool result to conversation
                    api_messages.append({
                        "role": "assistant",
                        "content": [
                            c for c in [
                                {"type": "text", "text": response.content} if response.content else None,
                                {
                                    "type": "tool_use",
                                    "id": tool_call["id"],
                                    "name": tool_call["name"],
                                    "input": tool_call["input"],
                                },
                            ] if c is not None
                        ]
                    })

                    api_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call["id"],
                                "content": json.dumps(tool_result),
                            }
                        ],
                    })

            # If the loop ended without streaming any text to the user, make one
            # final call to force a text summary from the LLM.
            if not streamed:
                logger.info("No text streamed after tool loop. Forcing final text response.")
                yield SSEEvent(event="status", data={"message": "Generando analisis..."})
                api_messages.append({
                    "role": "user",
                    "content": "Ahora presenta tu análisis completo basado en los datos que consultaste. Responde con texto, no ejecutes más consultas.",
                })
                final_response = self.llm.generate(system_prompt, api_messages, tools)
                if final_response.content:
                    clean_text, suggestions = _extract_suggestions(final_response.content)
                    assistant_text = clean_text
                    yield SSEEvent(event="token", data={"text": clean_text})
                    if suggestions:
                        yield SSEEvent(event="follow_up_suggestions", data={"suggestions": suggestions})

            # Save assistant response
            self.session_service.add_message(
                session_id,
                Message(
                    role="assistant",
                    content=assistant_text,
                    sql_query=sql_query,
                    visualization=viz_config,
                ),
            )

            yield SSEEvent(event="done", data={"session_id": session_id})

        except Exception as e:
            yield SSEEvent(event="error", data={"message": str(e)})

    def _dispatch_tool(self, tool_call: dict) -> dict:
        name = tool_call["name"]
        inputs = tool_call["input"]

        if name == "query_database":
            try:
                logger.info("LLM generated SQL: %s", inputs["sql"])
                results = self.query_service.validate_and_execute(inputs["sql"])
                if not results:
                    return {"results": [], "message": "La consulta no retorno resultados. Intenta con criterios mas amplios."}
                logger.info("Query returned %d rows", len(results))
                return {"results": results[:50], "total_rows": len(results)}
            except (ValueError, TimeoutError) as e:
                logger.warning("SQL validation/execution failed: %s | SQL: %s", e, inputs.get("sql"))
                return {"error": str(e)}
            except Exception as e:
                logger.error("Unexpected query error: %s | SQL: %s", e, inputs.get("sql"))
                return {"error": f"Error ejecutando query: {str(e)}"}

        elif name == "generate_visualization":
            return {"status": "visualization_created"}

        return {"error": f"Unknown tool: {name}"}
