from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "SORIA AI Prospecting Platform"
    APP_ENV: str = "local"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "postgresql+psycopg://soria:soria@localhost:5432/soria_prospecting"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    SECRET_KEY: str = "change-me"
    LOG_LEVEL: str = "INFO"

    # AI draft generation defaults
    AI_DRAFT_PROVIDER: str = "mock_ai"
    AI_DRAFT_PROMPT_PROFILE: str = "prospecting_fr_v1"
    AI_DRAFT_MODEL_NAME: str = "mock-soria-v1"
    AI_DRAFT_PROMPT_VERSION: str = "ai-draft-v1"

    # ------------------------------------------------------------------
    # External source API configuration (Phase 10A)
    # ------------------------------------------------------------------
    EXTERNAL_SOURCES_MODE: str = "mock"
    FRANCE_TRAVAIL_CLIENT_ID: Optional[str] = None
    FRANCE_TRAVAIL_CLIENT_SECRET: Optional[str] = None
    FRANCE_TRAVAIL_TOKEN_URL: Optional[str] = None
    FRANCE_TRAVAIL_API_BASE_URL: Optional[str] = None
    ADZUNA_UK_APP_ID: Optional[str] = None
    ADZUNA_UK_APP_KEY: Optional[str] = None
    ADZUNA_UK_API_BASE_URL: Optional[str] = None
    FREELANCER_OAUTH_TOKEN: Optional[str] = None
    FREELANCER_API_BASE_URL: Optional[str] = None
    JOOBLE_API_KEY: Optional[str] = None
    JOOBLE_API_BASE_URL: Optional[str] = None
    EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS: int = 10


settings = Settings()
