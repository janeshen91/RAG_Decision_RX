from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.service import RAGService


@lru_cache
def get_service() -> RAGService:
    return RAGService(get_settings())
