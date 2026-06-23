from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import chromadb

from app.chunking.text_chunker import TextChunk
from app.config import Settings
from app.embeddings.base import EmbeddingModel


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    source_type: str
    score: float
    chunk_index: int


def _collection_name(base: str, embedder_name: str) -> str:
    """Namespace the collection by embedder so vectors from different providers
    (or dimensions) are never stored in the same collection. A short stable hash
    of the embedder name is always appended, so providers stay separated even
    when a long base forces truncation (truncating the base, never the hash).
    Chroma requires 3-63 chars from [a-zA-Z0-9._-], starting/ending alphanumeric."""
    base_s = re.sub(r"[^a-zA-Z0-9._-]", "-", base)
    emb_s = re.sub(r"[^a-zA-Z0-9._-]", "-", embedder_name)
    digest = hashlib.sha1(embedder_name.encode("utf-8")).hexdigest()[:8]

    suffix = f"__{emb_s}__{digest}"
    if len(suffix) > 61:  # pathologically long embedder name: keep only the hash
        suffix = f"__{digest}"
    name = f"{base_s[: 63 - len(suffix)]}{suffix}"[:63]

    name = re.sub(r"^[^a-zA-Z0-9]+", "", name)
    return re.sub(r"[^a-zA-Z0-9]+$", "", name)


class ChromaVectorStore:
    def __init__(self, settings: Settings, embedder: EmbeddingModel) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.embedder_name = embedder.name
        self.dimension = int(embedder.dimension)

        name = _collection_name(settings.chroma_collection, embedder.name)
        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"embedder": embedder.name, "dimension": self.dimension},
        )

        # Guard against reusing a collection built with an incompatible embedder.
        # Namespacing already separates providers; this verifies both the embedder
        # identity and the dimension, catching a config change under the same name
        # (e.g. a reconfigured hash size) or any hash-collision edge case.
        meta = self.collection.metadata or {}
        existing_emb = meta.get("embedder")
        existing_dim = meta.get("dimension")
        if (existing_emb is not None and existing_emb != embedder.name) or (
            existing_dim is not None and int(existing_dim) != self.dimension
        ):
            raise ValueError(
                f"Chroma collection '{name}' was built with embedder "
                f"'{existing_emb}' (dimension {existing_dim}), but the current embedder "
                f"is '{embedder.name}' (dimension {self.dimension}). Reset the store "
                f"(delete '{settings.chroma_path}') or switch back to the original provider."
            )

    def upsert_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metas = [
            {
                "doc_id": c.doc_id,
                "source": c.source,
                "source_type": c.source_type,
                "chunk_index": c.chunk_index,
                # Best-effort optional fields (date/project/author) are only
                # present when they were actually extracted at ingestion.
                **c.metadata,
            }
            for c in chunks
        ]
        self.collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        return len(chunks)

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        result: dict[str, Any] = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where or None,
        )

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for chunk_id, text, meta, dist in zip(ids, docs, metas, dists):
            score = 1.0 / (1.0 + float(dist))
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    source=meta.get("source", "unknown"),
                    source_type=meta.get("source_type", "unknown"),
                    score=score,
                    chunk_index=int(meta.get("chunk_index", 0)),
                )
            )
        return chunks

    def count(self) -> int:
        return self.collection.count()
