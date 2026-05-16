from __future__ import annotations

from app.config import Settings
from app.llm.mock_client import MockLLMClient
from app.llm.openai_client import OpenAILLMClient


def get_llm_client(settings: Settings):
    provider = settings.llm_provider.lower().strip()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockLLMClient()
