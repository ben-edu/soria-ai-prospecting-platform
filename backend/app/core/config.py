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


settings = Settings()
