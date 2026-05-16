from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    text: str
    source: str
    source_type: str
    chunk_index: int


def chunk_text(
    *,
    doc_id: str,
    text: str,
    source: str,
    source_type: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    clean = " ".join(text.split())
    if not clean:
        return []

    chunks: list[TextChunk] = []
    step = chunk_size - chunk_overlap
    start = 0
    idx = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunk_body = clean[start:end]
        chunks.append(
            TextChunk(
                chunk_id=f"{doc_id}::chunk::{idx}",
                doc_id=doc_id,
                text=chunk_body,
                source=source,
                source_type=source_type,
                chunk_index=idx,
            )
        )
        idx += 1
        start += step

    return chunks
