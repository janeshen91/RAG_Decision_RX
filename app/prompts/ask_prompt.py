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
        "supporting_evidence, claims, unknowns, confidence, limitations.\n\n"
        "Each item in `claims` is an object with: text; explicit_or_inferred (exactly "
        "one of \"explicit\", \"inferred\", \"unknown\"); evidence_ids (a list of the "
        "[E#] labels above that support the claim); confidence (0-1). Label a claim "
        "\"explicit\" ONLY if it is directly stated in the cited evidence, \"inferred\" "
        "if you synthesized it, and \"unknown\" if the evidence raises but does not "
        "resolve it. An \"explicit\" claim MUST cite at least one [E#] label. "
        "`unknowns` is a list of open questions the evidence does not answer."
    )
