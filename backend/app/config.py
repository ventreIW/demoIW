from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DemoIW Backend"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/demoiw"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    # OpenRouter settings
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    MODEL_DATA_ENRICHMENT: str = ""
    MODEL_COMMUNICATIONS: str = ""

    #: NFR-06 operator identifier used when a request carries no ``X-Operator-Id`` header.
    #: This product has no authentication (B-17 is still under consideration), so the
    #: default names itself as a placeholder. A plausible-looking username here would
    #: falsify the audit record, which is worse than an obviously unknown one.
    DEFAULT_OPERATOR_ID: str = "demo-operator (unauthenticated)"
    MODEL_NL_QUERY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
