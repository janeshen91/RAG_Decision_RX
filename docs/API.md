# API Usage Guide

Base URL (local): `http://127.0.0.1:8000`

## 1) Health Check

### Request
```bash
curl -s http://127.0.0.1:8000/health
```

### Example Response
```json
{
  "status": "ok",
  "indexed_chunks": 0
}
```

## 2) Ingest Files

Ingests `.txt`, `.pdf`, `.docx` from a local directory path.

### Request
```bash
curl -s -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/absolute/path/to/your/docs"
  }'
```

### Example Response
```json
{
  "documents_ingested": 3,
  "chunks_indexed": 14
}
```

## 3) Add Institutional Note

Adds a manual note and indexes it like normal documents.

### Request
```bash
curl -s -X POST http://127.0.0.1:8000/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q2 procurement update",
    "text": "Supplier lead time improved from 12 weeks to 8 weeks."
  }'
```

### Example Response
```json
{
  "note_id": "note::3c658a59-c0b1-47d6-86ce-c4f6f2f3fc26",
  "chunks_indexed": 1
}
```

## 4) Ask a Question

Retrieves relevant chunks, prompts the LLM using only retrieved evidence, and returns structured JSON.

### Request
```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What changed in supplier lead times?",
    "top_k": 5
  }'
```

### Example Response
```json
{
  "answer_summary": "Supplier lead time improved from 12 weeks to 8 weeks.",
  "rationale_breakdown": {
    "scientific": "No explicit scientific finding in retrieved evidence.",
    "business": "Faster lead times may improve fulfillment reliability.",
    "supply_chain": "Evidence indicates a reduction from 12 to 8 weeks.",
    "timeline": "Change is described as current-state update; no exact date provided.",
    "regulatory": "No regulatory detail found in retrieved evidence.",
    "unknown_or_mixed": "Some categories are not directly supported by evidence."
  },
  "supporting_evidence": [
    {
      "chunk_id": "note::3c658a59-c0b1-47d6-86ce-c4f6f2f3fc26::chunk::0",
      "source": "Q2 procurement update",
      "source_type": "note",
      "score": 0.83,
      "snippet": "Supplier lead time improved from 12 weeks to 8 weeks."
    }
  ],
  "confidence": 0.83,
  "limitations": [
    "Answer is based on limited retrieved context."
  ]
}
```

## Swagger UI

Interactive API docs are available at:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`
