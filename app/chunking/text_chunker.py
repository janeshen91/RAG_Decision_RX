from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    text: str
    source: str
    source_type: str
    chunk_index: int
    metadata: dict[str, str] = field(default_factory=dict)


def chunk_text(
    *,
    doc_id: str,
    text: str,
    source: str,
    source_type: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata: dict[str, str] | None = None,
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
                metadata=dict(metadata or {}),
            )
        )
        idx += 1
        start += step

    return chunks
