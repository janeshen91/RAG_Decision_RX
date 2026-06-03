from __future__ import annotations

from typing import Protocol


class EmbeddingModel(Protocol):
    @property
    def name(self) -> str:
        """Stable identifier (provider + model) used to namespace vector collections."""
        ...

    @property
    def dimension(self) -> int:
        """Length of the produced embedding vectors."""
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
