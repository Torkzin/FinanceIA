from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "finance-ai-api"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    jwt_secret_key: SecretStr = SecretStr("development-only-change-me-at-least-32-characters")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "finance_ai_refresh"
    demo_user_password: SecretStr = SecretStr("FinanceAI123!")
    document_storage_path: str = "/app/storage"
    max_upload_size_mb: int = 10
    ai_provider: str = "demo"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    database_url: str = "postgresql+asyncpg://finance_ai:finance_ai_dev@localhost:5432/finance_ai"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def reject_default_production_secret(self) -> "Settings":
        if (
            self.app_env == "production"
            and self.jwt_secret_key.get_secret_value()
            == "development-only-change-me-at-least-32-characters"
        ):
            raise ValueError("JWT_SECRET_KEY must be configured in production")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
