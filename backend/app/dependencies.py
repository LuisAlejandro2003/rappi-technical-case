from functools import lru_cache

from app.core.config import Settings
from app.core.database import DuckDBService


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
