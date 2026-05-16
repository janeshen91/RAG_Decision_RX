from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_service
from app.api.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    NoteRequest,
    NoteResponse,
)
from app.service import RAGService


router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(req: IngestRequest, service: RAGService = Depends(get_service)) -> IngestResponse:
    try:
        docs, chunks = service.ingest_directory(req.directory)
        return IngestResponse(documents_ingested=docs, chunks_indexed=chunks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest, service: RAGService = Depends(get_service)) -> AskResponse:
    payload = service.ask(question=req.question, top_k=req.top_k)
    return AskResponse(**payload)


@router.post("/notes", response_model=NoteResponse)
def add_note(req: NoteRequest, service: RAGService = Depends(get_service)) -> NoteResponse:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")

    note_id, chunks = service.add_note(title=req.title, text=req.text)
    return NoteResponse(note_id=note_id, chunks_indexed=chunks)


@router.get("/health", response_model=HealthResponse)
def health_check(service: RAGService = Depends(get_service)) -> HealthResponse:
    return HealthResponse(**service.health())
