from __future__ import annotations

from pathlib import Path

from app.ingestion.metadata import extract_basic_metadata, infer_source_type


def test_infer_source_type_from_filename() -> None:
    assert infer_source_type(Path("scientific_study.txt")) == "study"
    assert infer_source_type(Path("regulatory_summary.txt")) == "summary"
    assert infer_source_type(Path("supply_chain_note.txt")) == "note"
    assert infer_source_type(Path("timeline.txt")) == "timeline"
    assert infer_source_type(Path("business_analysis.txt")) == "analysis"


def test_infer_source_type_from_parent_folder() -> None:
    assert infer_source_type(Path("meeting transcripts/2024-01.txt")) == "meeting"
    assert infer_source_type(Path("protocols/assay_prep.txt")) == "sop"


def test_infer_source_type_defaults_to_file() -> None:
    assert infer_source_type(Path("random_document.txt")) == "file"


def test_extract_basic_metadata_finds_present_fields_only() -> None:
    text = "Author: Jane Doe\nProject: Affinity Evolution\nBody text here."
    meta = extract_basic_metadata(Path("2010-03-18_report.txt"), text)
    assert meta["author"] == "Jane Doe"
    assert meta["project"] == "Affinity Evolution"
    assert meta["date"] == "2010-03-18"


def test_extract_basic_metadata_omits_absent_fields() -> None:
    meta = extract_basic_metadata(Path("plain.txt"), "No structured fields here.")
    assert meta == {}


def test_extract_basic_metadata_rejects_invalid_date() -> None:
    # Out-of-range month/day must not be captured.
    assert "date" not in extract_basic_metadata(Path("2010-13-40.txt"), "")


def test_extract_basic_metadata_rejects_calendar_invalid_date() -> None:
    # 2010-02-31 is well-formed but not a real calendar date.
    assert "date" not in extract_basic_metadata(Path("2010-02-31_report.txt"), "")
