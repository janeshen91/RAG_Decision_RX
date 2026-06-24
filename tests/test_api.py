from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_service
from app.main import app
from app.config import Settings
from app.service import RAGService


def build_test_client(tmp_path: Path) -> TestClient:
    chroma_dir = tmp_path / "chroma"
    settings = Settings(chroma_path=str(chroma_dir), llm_provider="mock")
    service = RAGService(settings)

    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def test_health(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_ingest_and_ask(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "trial.txt").write_text(
        "Compound A reduced inflammatory markers by 30 percent in a small study.",
        encoding="utf-8",
    )

    client = build_test_client(tmp_path)

    ingest = client.post("/ingest", json={"directory": str(docs_dir)})
    assert ingest.status_code == 200
    ingest_body = ingest.json()
    assert ingest_body["documents_ingested"] == 1
    assert ingest_body["chunks_indexed"] >= 1

    ask = client.post("/ask", json={"question": "What happened to inflammatory markers?", "top_k": 3})
    assert ask.status_code == 200
    body = ask.json()

    assert "answer_summary" in body
    assert "rationale_breakdown" in body
    assert "supporting_evidence" in body
    assert "confidence" in body
    assert "limitations" in body
    assert body["supporting_evidence"]


def test_homepage_renders_evidence_with_snippet(tmp_path: Path) -> None:
    # Guards the PR-1 fix: the evidence viewer must read `item.snippet`
    # (the EvidenceItem schema field), not the non-existent `item.text`,
    # otherwise the UI renders "- undefined" for every evidence item.
    client = build_test_client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "item.snippet" in html
    assert "item.text" not in html
    # Limitations must be rendered line-by-line, not interpolated raw
    # (which would coerce the array to a comma-joined string).
    assert "(data.limitations || [])" in html


def test_ingest_infers_source_type_and_filters(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "alpha_study.txt").write_text(
        "Compound A reduced inflammatory markers in the study cohort.",
        encoding="utf-8",
    )
    (docs_dir / "beta_note.txt").write_text(
        "Internal note: supplier lead time improved from 12 to 8 weeks.",
        encoding="utf-8",
    )

    client = build_test_client(tmp_path)
    assert client.post("/ingest", json={"directory": str(docs_dir)}).status_code == 200

    # Unfiltered: source_type is inferred from the filenames, not hardcoded "file".
    unfiltered = client.post("/ask", json={"question": "anything", "top_k": 5}).json()
    types = {item["source_type"] for item in unfiltered["supporting_evidence"]}
    assert types == {"study", "note"}

    # Filtered: only chunks matching the requested source_type come back.
    filtered = client.post(
        "/ask",
        json={"question": "anything", "top_k": 5, "filters": {"source_type": "study"}},
    ).json()
    assert filtered["supporting_evidence"]
    assert {item["source_type"] for item in filtered["supporting_evidence"]} == {"study"}


def test_ask_rejects_unsupported_filter_field(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    resp = client.post(
        "/ask",
        json={"question": "anything", "filters": {"bogus": "x", "$and": "y"}},
    )
    assert resp.status_code == 400
    assert "Unsupported filter field" in resp.json()["detail"]


def test_ask_multi_key_filter(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    # Both are studies; only one carries Project: Apollo.
    (docs_dir / "alpha_study.txt").write_text(
        "Project: Apollo\nCompound A reduced markers in the study cohort.",
        encoding="utf-8",
    )
    (docs_dir / "beta_study.txt").write_text(
        "Compound B study results with no project tag.",
        encoding="utf-8",
    )

    client = build_test_client(tmp_path)
    assert client.post("/ingest", json={"directory": str(docs_dir)}).status_code == 200

    filtered = client.post(
        "/ask",
        json={
            "question": "anything",
            "top_k": 5,
            "filters": {"source_type": "study", "project": "Apollo"},
        },
    ).json()
    assert filtered["supporting_evidence"]
    assert all("alpha_study" in item["source"] for item in filtered["supporting_evidence"])


def test_ask_returns_grounded_labeled_claims(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "trial.txt").write_text(
        "Compound A reduced inflammatory markers by 30 percent in a small study.",
        encoding="utf-8",
    )

    client = build_test_client(tmp_path)
    assert client.post("/ingest", json={"directory": str(docs_dir)}).status_code == 200

    body = client.post("/ask", json={"question": "What did the study find?", "top_k": 3}).json()
    assert "claims" in body and "unknowns" in body
    assert body["claims"]

    evidence_ids = {item["chunk_id"] for item in body["supporting_evidence"]}
    for claim in body["claims"]:
        assert claim["explicit_or_inferred"] in {"explicit", "inferred", "unknown"}
        # Every cited evidence id must be a real retrieved chunk.
        assert set(claim["evidence_ids"]) <= evidence_ids
        # Explicit claims must be grounded in at least one evidence id.
        if claim["explicit_or_inferred"] == "explicit":
            assert claim["evidence_ids"]


def test_notes_endpoint(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    note_resp = client.post(
        "/notes",
        json={
            "title": "Internal procurement update",
            "text": "Supplier lead time improved from 12 weeks to 8 weeks.",
        },
    )
    assert note_resp.status_code == 200
    note_body = note_resp.json()
    assert note_body["note_id"].startswith("note::")
    assert note_body["chunks_indexed"] >= 1

    ask = client.post("/ask", json={"question": "What is the supplier lead time?", "top_k": 2})
    assert ask.status_code == 200
    ask_body = ask.json()
    assert len(ask_body["supporting_evidence"]) >= 1
