from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb

from app.chunking.text_chunker import TextChunk
from app.config import Settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    source_type: str
    score: float
    chunk_index: int


class ChromaVectorStore:
    def __init__(self, settings: Settings) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.client.get_or_create_collection(name=settings.chroma_collection)

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
            }
            for c in chunks
        ]
        self.collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        return len(chunks)

    def query(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedChunk]:
        result: dict[str, Any] = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)

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
