from functools import lru_cache

from app.core.config import Settings
from app.core.database import DuckDBService
from app.services.session_service import SessionService
from app.services.query_service import QueryService
from app.services.chat_service import ChatService
from app.services.llm_provider import ClaudeLLMProvider


@lru_cache
def get_settings() -> Settings:
    return Settings()


_db_service: DuckDBService | None = None


def get_db() -> DuckDBService:
    global _db_service
    if _db_service is None:
        settings = get_settings()
        _db_service = DuckDBService(data_dir=settings.duckdb_data_dir)
    return _db_service


_session_service: SessionService | None = None
_query_service: QueryService | None = None
_chat_service: ChatService | None = None


def get_session_service() -> SessionService:
    global _session_service
    if _session_service is None:
        _session_service = SessionService()  # in-memory SQLite
    return _session_service


def get_query_service() -> QueryService:
    global _query_service
    if _query_service is None:
        _query_service = QueryService(get_db(), get_settings())
    return _query_service


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        settings = get_settings()
        llm = ClaudeLLMProvider(api_key=settings.anthropic_api_key, model=settings.claude_model)
        _chat_service = ChatService(
            llm=llm,
            query_service=get_query_service(),
            session_service=get_session_service(),
            settings=settings,
        )
    return _chat_service
