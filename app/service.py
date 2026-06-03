from __future__ import annotations

import uuid

from app.chunking.text_chunker import TextChunk, chunk_text
from app.config import Settings
from app.embeddings.factory import get_embedding_model
from app.ingestion.file_loader import RawDocument, load_documents_from_directory
from app.llm.factory import get_llm_client
from app.prompts.ask_prompt import build_ask_prompt
from app.retrieval.vector_store import ChromaVectorStore


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = get_embedding_model(settings)
        self.vector_store = ChromaVectorStore(settings, self.embedder)
        self.llm = get_llm_client(settings)

    def _chunk_documents(self, docs: list[RawDocument]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for doc in docs:
            chunks.extend(
                chunk_text(
                    doc_id=doc.doc_id,
                    text=doc.text,
                    source=doc.source,
                    source_type=doc.source_type,
                    chunk_size=self.settings.chunk_size,
                    chunk_overlap=self.settings.chunk_overlap,
                    metadata=doc.metadata,
                )
            )
        return chunks

    def ingest_directory(self, directory: str) -> tuple[int, int]:
        docs = load_documents_from_directory(directory)
        chunks = self._chunk_documents(docs)
        embeddings = self.embedder.embed_texts([c.text for c in chunks]) if chunks else []
        indexed = self.vector_store.upsert_chunks(chunks, embeddings)
        return len(docs), indexed

    def add_note(self, title: str, text: str) -> tuple[str, int]:
        note_id = f"note::{uuid.uuid4()}"
        doc = RawDocument(doc_id=note_id, source=title, text=text, source_type="note")
        chunks = self._chunk_documents([doc])
        embeddings = self.embedder.embed_texts([c.text for c in chunks]) if chunks else []
        indexed = self.vector_store.upsert_chunks(chunks, embeddings)
        return note_id, indexed

    def ask(self, question: str, top_k: int = 5, filters: dict[str, str] | None = None) -> dict:
        q_emb = self.embedder.embed_query(question)
        retrieved = self.vector_store.query(q_emb, top_k=top_k, where=_build_where(filters))
        evidence = [
            {
                "chunk_id": c.chunk_id,
                "source": c.source,
                "source_type": c.source_type,
                "score": round(c.score, 4),
                "snippet": c.text,
            }
            for c in retrieved
        ]

        prompt = build_ask_prompt(question, retrieved)
        answer = self.llm.generate_structured_answer(prompt=prompt, evidence=evidence)

        answer.setdefault("answer_summary", "")
        answer.setdefault(
            "rationale_breakdown",
            {
                "scientific": "",
                "business": "",
                "supply_chain": "",
                "timeline": "",
                "regulatory": "",
                "unknown_or_mixed": "",
            },
        )
        answer["supporting_evidence"] = evidence
        answer.setdefault("confidence", 0.0)
        answer.setdefault("limitations", [])

        return _normalize_answer(answer)

    def health(self) -> dict:
        return {"status": "ok", "indexed_chunks": self.vector_store.count()}


# Metadata fields a client is allowed to filter on. Restricting this prevents
# arbitrary/operator keys (e.g. "$and") from being passed straight to Chroma,
# which would surface as a 500 instead of a clean client error.
_ALLOWED_FILTER_FIELDS = frozenset({"source_type", "date", "project", "author"})


def _build_where(filters: dict[str, str] | None) -> dict | None:
    """Translate a flat field->value filter map into Chroma's `where` syntax.
    Chroma requires an explicit `$and` when filtering on more than one field.
    Raises ValueError for unsupported filter fields."""
    if not filters:
        return None
    invalid = [field for field in filters if field not in _ALLOWED_FILTER_FIELDS]
    if invalid:
        allowed = ", ".join(sorted(_ALLOWED_FILTER_FIELDS))
        raise ValueError(f"Unsupported filter field(s): {invalid}. Allowed: {allowed}.")
    clauses = [{field: value} for field, value in filters.items()]
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _normalize_answer(payload: dict) -> dict:
    return {
        "answer_summary": str(payload.get("answer_summary", "")),
        "rationale_breakdown": dict(payload.get("rationale_breakdown", {})),
        "supporting_evidence": list(payload.get("supporting_evidence", [])),
        "confidence": float(payload.get("confidence", 0.0)),
        "limitations": [str(x) for x in payload.get("limitations", [])],
    }
