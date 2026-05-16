# DecisionsRX RAG MVP (FastAPI)

Minimal RAG API that ingests local `.txt`, `.pdf`, `.docx` files, chunks text, embeds chunks, stores vectors in local Chroma, and answers questions with evidence-backed structured JSON.

## Features
- FastAPI endpoints:
  - `POST /ingest`
  - `POST /ask`
  - `POST /notes`
  - `GET /health`
- File ingestion from local directory (`.txt`, `.pdf`, `.docx`)
- Chunking + embedding + Chroma vector storage
- Manual institutional notes indexed exactly like documents
- Modular code layout for easy extension
- Swappable LLM provider (`mock` default, `openai` optional)
- Basic tests

## Project Structure
- `app/ingestion` - file parsing/loading
- `app/chunking` - chunking logic
- `app/embeddings` - embedding interfaces + local embedding model
- `app/retrieval` - vector store + retrieval
- `app/prompts` - ask prompt construction
- `app/llm` - provider abstraction and implementations
- `app/api` - request/response schemas and routes
- `app/evaluation` - simple evaluation helpers

## Setup
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and adjust values if needed:

```bash
cp .env.example .env
```

3. Run the API:

```bash
uvicorn app.main:app --reload
```

Open the UI at: `http://127.0.0.1:8000/`

API docs: `http://127.0.0.1:8000/docs`

## Environment Variables
See `.env.example`.

Important values:
- `CHROMA_PATH`: local vector DB storage path
- `CHROMA_COLLECTION`: collection name
- `LLM_PROVIDER`: `mock` or `openai`
- `OPENAI_API_KEY`: required only if `LLM_PROVIDER=openai`

## Endpoint Usage

### `POST /ingest`
Request:

```json
{
  "directory": "/absolute/path/to/local/docs"
}
```

### `POST /notes`
Request:

```json
{
  "title": "Q2 market signal",
  "text": "Institutional note content here"
}
```

### `POST /ask`
Request:

```json
{
  "question": "What evidence exists for adoption risk?",
  "top_k": 5
}
```

Response includes:
- `answer_summary`
- `rationale_breakdown`:
  - `scientific`
  - `business`
  - `supply_chain`
  - `timeline`
  - `regulatory`
  - `unknown_or_mixed`
- `supporting_evidence`
- `confidence`
- `limitations`

## Tests

```bash
pytest -q
```

## Notes
- This is an MVP focused on readability and quick iteration.
- Default `mock` LLM is deterministic and offline-friendly for development/testing.
- OpenAI support is included behind an interface so providers can be swapped later.
