import json
import logging
from typing import AsyncGenerator

from app.core.config import Settings

logger = logging.getLogger(__name__)
from app.services.llm_provider import LLMProvider, LLMResponse
from app.services.query_service import QueryService
from app.services.session_service import SessionService
from app.models.schemas import Message, VizConfig, SSEEvent


SYSTEM_PROMPT_TEMPLATE = """You are Rappi Analytics Assistant, an AI chatbot that helps non-technical users analyze Rappi's operational data.

## Your Role
- Translate natural language questions into SQL queries against DuckDB
- Present results in a clear, helpful format
- Suggest visualizations when appropriate
- Respond in the same language the user writes (Spanish, Portuguese, or English)

## IMPORTANT: Available Tables
You ONLY have access to these 3 tables. Do NOT reference any other table names:
1. raw_input_metrics — operational KPIs by zone (COUNTRY, CITY, ZONE, ZONE_TYPE, ZONE_PRIORITIZATION, METRIC, L8W_ROLL..L0W_ROLL)
2. raw_orders — order counts by zone (COUNTRY, CITY, ZONE, METRIC, L8W..L0W)
3. raw_summary — metadata/glossary (Column, Type, Examples, "Description (inferred)")

Data is aggregated at the ZONE level (not restaurant or store level). If a user asks about individual restaurants/stores, explain that data is available at zone level and offer zone-level analysis instead.

## Database Schema (DDL + samples)
{schema_context}

## SQL Guidelines for DuckDB
- Use ONLY the column names shown in the DDL above
- For raw_input_metrics: week columns are L8W_ROLL, L7W_ROLL, ..., L0W_ROLL (DOUBLE)
- For raw_orders: week columns are L8W, L7W, ..., L0W (BIGINT)
- L0W/L0W_ROLL = most recent week, L8W/L8W_ROLL = 8 weeks ago
- METRIC column in raw_input_metrics contains metric names like 'Gross Profit UE', 'Perfect Orders', etc.
- METRIC column in raw_orders always contains 'Orders'
- Use single quotes for string literals: WHERE COUNTRY = 'CO'
- Always include a LIMIT clause (max 100 rows)

## Business Context
- "Zonas problematicas" = zones with deteriorating metrics (L0W worse than L4W)
- "Crecimiento" / "mejora" = positive trend (L0W better than L4W)
- "Esta semana" = L0W (most recent week), "Semana pasada" = L1W
- Zone types: 'Wealthy', 'Non Wealthy'
- Zone priorities: 'High Priority', 'Prioritized', 'Not Prioritized'
- Countries: AR, BR, CL, CO, CR, EC, MX, PE, UY

## Rules
1. ALWAYS use the query_database tool to get data. NEVER make up numbers.
2. Write ONE correct SQL query on your first attempt using the exact column/table names above.
3. If a query fails, read the error carefully and fix the specific issue.
4. When data is a time series (multiple weeks), use generate_visualization with type "line".
5. When comparing categories (countries, zones, types), use generate_visualization with type "bar".
6. For rankings or lists, present as formatted text.
7. If the user asks about data not in these tables (e.g., individual restaurants, couriers, products), explain what IS available and suggest the closest analysis.
8. Always explain what the data shows after presenting results.
9. Use the metrics dictionary to understand metric definitions accurately.
"""

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
    ):
        self.llm = llm
        self.query_service = query_service
        self.session_service = session_service
        self.settings = settings
        self._system_prompt: str | None = None

    def build_system_prompt(self) -> str:
        if self._system_prompt is None:
            schema_ctx = self.query_service.get_schema_context()
            self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema_context=schema_ctx)
        return self._system_prompt

    def build_tools(self) -> list[dict]:
        return TOOLS

    async def process_message(
        self, session_id: str | None, user_message: str
    ) -> AsyncGenerator[SSEEvent, None]:
        # Create or get session
        if session_id is None:
            session_id = self.session_service.create_session()

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

        system_prompt = self.build_system_prompt()
        tools = self.build_tools()

        try:
            # Tool loop
            max_iterations = 5
            assistant_text = ""
            viz_config = None
            sql_query = None

            for _ in range(max_iterations):
                response = self.llm.generate(system_prompt, api_messages, tools)

                if response.content:
                    assistant_text += response.content
                    yield SSEEvent(event="token", data={"text": response.content})

                if not response.tool_calls or response.stop_reason == "end_turn":
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
