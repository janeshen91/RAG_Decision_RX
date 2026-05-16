from __future__ import annotations

from app.retrieval.vector_store import RetrievedChunk


def build_ask_prompt(question: str, evidence_chunks: list[RetrievedChunk]) -> str:
    evidence_block = "\n\n".join(
        [
            f"[E{i+1}] source={chunk.source} score={chunk.score:.3f}\n{chunk.text}"
            for i, chunk in enumerate(evidence_chunks)
        ]
    )

    return (
        "You are an assistant for institutional decision support. "
        "Answer ONLY from the supplied evidence. If evidence is missing, state uncertainty clearly.\n\n"
        f"Question:\n{question}\n\n"
        "Evidence:\n"
        f"{evidence_block}\n\n"
        "Return valid JSON with keys: answer_summary, rationale_breakdown "
        "(scientific, business, supply_chain, timeline, regulatory, unknown_or_mixed), "
        "supporting_evidence, confidence, limitations."
    )
