from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "sqlite:///./data/grammar_agent.db"
    timezone: str = "Asia/Shanghai"
    daily_lesson_hour: int = Field(default=7, ge=0, le=23)
    daily_lesson_minute: int = Field(default=30, ge=0, le=59)
    default_user_id: str = "local-user"

    llm_provider: str = "openai"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_verification_token: str | None = None
    feishu_encrypt_key: str | None = None
    feishu_receive_id_type: str = "open_id"
    feishu_default_receive_id: str | None = None

    @property
    def active_llm_api_key(self) -> str | None:
        return self.llm_api_key or self.openai_api_key

    @property
    def active_llm_model(self) -> str:
        return self.llm_model or self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
