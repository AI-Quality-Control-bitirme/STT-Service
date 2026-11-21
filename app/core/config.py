from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "STT Service"
    app_env: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = (
        "postgresql+psycopg://stt_user:stt_pass@localhost:5432/stt_db"
    )

    stt_provider: str = "local"
    local_whisper_model: str = "tiny"
    local_whisper_device: str = "cpu"
    local_whisper_compute_type: str = "int8"
    openai_api_key: str | None = None
    openai_whisper_model: str = "whisper-1"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()