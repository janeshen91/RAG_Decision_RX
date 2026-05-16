from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DecisionsRX RAG MVP"
    chroma_path: str = Field(default="data/chroma")
    chroma_collection: str = Field(default="decisionsrx")

    chunk_size: int = Field(default=800)
    chunk_overlap: int = Field(default=120)

    llm_provider: str = Field(default="mock")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_api_key: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
