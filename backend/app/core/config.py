from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.aws_secrets import load_aws_runtime_settings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Kyron Medical Clinical Assistant API"
    app_env: str = "development"
    app_debug: bool = False

    host: str = "127.0.0.1"
    port: int = 8000

    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"

    database_url: str = Field(..., alias="DATABASE_URL")
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle_seconds: int = 1800
    database_pool_pre_ping: bool = True
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    auth_cookie_name: str = "kyron_access_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    llm_provider: str = "openai"
    openai_api_key: str = "replace_with_openai_api_key"
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = 60.0
    voice_provider: str = "openai_realtime"
    openai_realtime_model: str = "gpt-realtime"
    openai_realtime_voice: str = "alloy"
    openai_realtime_session_url: str = "https://api.openai.com/v1/realtime/sessions"
    openai_realtime_create_remote_session: bool = False
    openai_realtime_transcription_model: str = "gpt-realtime-whisper"
    openai_realtime_transcription_language: str = "en"
    openai_realtime_transcription_delay: str = "low"

    anthropic_api_key: str = "replace_with_anthropic_api_key"
    anthropic_model: str = "claude-3-5-sonnet-latest"

    retell_api_key: str = "replace_with_retell_api_key"
    retell_agent_id: str = "replace_with_retell_agent_id"
    retell_webhook_secret: str = "replace_with_retell_webhook_secret"

    aws_access_key_id: str = "replace_with_aws_access_key_id"
    aws_secret_access_key: str = "replace_with_aws_secret_access_key"
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "replace_with_bucket_name"
    aws_use_runtime_secrets: bool = False
    aws_secrets_manager_secret_id: str | None = None
    aws_parameter_store_path: str | None = None

    icd_api_base_url: str = "replace_with_icd_api_base_url"
    icd_api_key: str = "replace_with_icd_api_key"

    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if settings.aws_use_runtime_secrets:
        runtime_settings = load_aws_runtime_settings(
            region=settings.aws_region,
            secrets_manager_secret_id=settings.aws_secrets_manager_secret_id,
            parameter_store_path=settings.aws_parameter_store_path,
        )
        if runtime_settings:
            settings = settings.model_copy(update=runtime_settings)

    return settings
