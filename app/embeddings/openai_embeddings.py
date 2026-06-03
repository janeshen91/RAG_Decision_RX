from __future__ import annotations

from openai import OpenAI


# Known output dimensions for OpenAI embedding models, so the vector store can
# namespace/validate collections without spending an API call. Unknown models
# fall back to a one-time probe (see ``dimension``).
_OPENAI_EMBED_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingModel:
    """Dense embeddings via the OpenAI embeddings API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._dimension = _OPENAI_EMBED_DIMS.get(model)

    @property
    def name(self) -> str:
        return f"openai-{self.model}"

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Unknown model: probe once and cache the result. NOTE: this is a
            # network call, and the vector store reads `dimension` at RAGService
            # init, so an unrecognised model triggers one API request on startup.
            # Models in _OPENAI_EMBED_DIMS (incl. the default) avoid this.
            self._dimension = len(self.embed_query("dimension probe"))
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=[text])
        return response.data[0].embedding
