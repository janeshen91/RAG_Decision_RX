from __future__ import annotations

from app.config import Settings
from app.embeddings.base import EmbeddingModel
from app.embeddings.hash_embeddings import HashEmbeddingModel
from app.embeddings.openai_embeddings import OpenAIEmbeddingModel


def get_embedding_model(settings: Settings) -> EmbeddingModel:
    provider = settings.embedding_provider.lower().strip()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddingModel(api_key=settings.openai_api_key, model=settings.openai_embedding_model)
    if provider in ("hash", ""):
        return HashEmbeddingModel()
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider!r}")
