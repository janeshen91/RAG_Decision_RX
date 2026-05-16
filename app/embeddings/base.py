from __future__ import annotations

from typing import Protocol


class EmbeddingModel(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
