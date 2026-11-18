from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    openai_api_key: SecretStr | None = None
    openai_chat_model: str = Field(default="gpt-6-luna", min_length=1)
    openai_embedding_model: Literal["text-embedding-3-small"] = "text-embedding-3-small"
    openai_cypher_model: str = Field(default="gpt-6.1-sol", min_length=1)
    qdrant_url: str = Field(default="http://localhost:6333", min_length=1)
    neo4j_uri: str = Field(default="bolt://localhost:7687", min_length=1)
    neo4j_username: str = Field(default="neo4j", min_length=1)
    neo4j_password: SecretStr = SecretStr("enterprise-demo-password")
    neo4j_database: str = Field(default="neo4j", min_length=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_startup() -> None:
    try:
        settings = get_settings()
    except ValidationError as exc:
        fields = ", ".join(str(error["loc"][0]).upper() for error in exc.errors(include_input=False))
        raise RuntimeError(f"Invalid backend configuration: {fields}.") from None
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
        raise RuntimeError("Set OPENAI_API_KEY in the backend environment before starting the API.")
