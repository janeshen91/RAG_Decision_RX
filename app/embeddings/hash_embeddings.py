from __future__ import annotations

import hashlib
import math
import re

from app.embeddings.base import EmbeddingModel


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class HashEmbeddingModel(EmbeddingModel):
    """Lightweight local embedding model for MVP/offline usage."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    @property
    def name(self) -> str:
        return f"hash-d{self.dimensions}"

    @property
    def dimension(self) -> int:
        return self.dimensions

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = TOKEN_RE.findall(text.lower())
        if not tokens:
            return vec

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], byteorder="little") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
