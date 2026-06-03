from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    directory: str = Field(..., description="Local directory containing .txt/.pdf/.docx files")


class IngestResponse(BaseModel):
    documents_ingested: int
    chunks_indexed: int


class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    filters: dict[str, str] | None = Field(
        default=None,
        description="Optional metadata filters, e.g. {\"source_type\": \"meeting\"}",
    )


class RationaleBreakdown(BaseModel):
    scientific: str = ""
    business: str = ""
    supply_chain: str = ""
    timeline: str = ""
    regulatory: str = ""
    unknown_or_mixed: str = ""


class EvidenceItem(BaseModel):
    chunk_id: str
    source: str
    source_type: str
    score: float
    snippet: str


class Claim(BaseModel):
    text: str
    explicit_or_inferred: str = Field(
        description="One of: explicit (stated in cited evidence), "
        "inferred (synthesized), unknown (raised but unresolved)."
    )
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class AskResponse(BaseModel):
    answer_summary: str
    rationale_breakdown: RationaleBreakdown
    supporting_evidence: list[EvidenceItem]
    claims: list[Claim] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    confidence: float
    limitations: list[str]


class NoteRequest(BaseModel):
    title: str
    text: str


class NoteResponse(BaseModel):
    note_id: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int
