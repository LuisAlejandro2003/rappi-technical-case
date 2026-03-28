from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = "not-set"
    claude_model: str = "claude-sonnet-4-20250514"
    duckdb_data_dir: str = "./data"
    max_query_retries: int = 2
    query_timeout_seconds: int = 5
    max_result_rows: int = 1000

    model_config = {"env_file": ("../.env", ".env"), "env_file_encoding": "utf-8"}
