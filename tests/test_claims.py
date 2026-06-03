from __future__ import annotations

from app.service import _normalize_claims


VALID_IDS = {"doc::chunk::0", "doc::chunk::1"}
LABEL_MAP = {"E1": "doc::chunk::0", "E2": "doc::chunk::1"}


def test_maps_evidence_labels_to_chunk_ids() -> None:
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "explicit", "evidence_ids": ["E1"]}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["evidence_ids"] == ["doc::chunk::0"]
    assert claims[0]["explicit_or_inferred"] == "explicit"


def test_maps_bracketed_evidence_labels_to_chunk_ids() -> None:
    # The prompt tells the model to cite "[E#]"; bracketed forms must still map.
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "explicit", "evidence_ids": ["[E1]", "[E2]"]}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["evidence_ids"] == ["doc::chunk::0", "doc::chunk::1"]
    assert claims[0]["explicit_or_inferred"] == "explicit"


def test_clamps_confidence_to_unit_interval() -> None:
    claims = _normalize_claims(
        [
            {"text": "high", "explicit_or_inferred": "inferred", "confidence": 5.0},
            {"text": "low", "explicit_or_inferred": "inferred", "confidence": -2.0},
        ],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["confidence"] == 1.0
    assert claims[1]["confidence"] == 0.0


def test_drops_unknown_evidence_ids() -> None:
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "inferred", "evidence_ids": ["E9", "nope"]}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["evidence_ids"] == []


def test_ungrounded_explicit_is_downgraded_to_inferred() -> None:
    # An explicit claim whose evidence ids are all invalid must not stay explicit
    # (enforces "no fabricated explicit claims").
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "explicit", "evidence_ids": ["bogus"]}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["explicit_or_inferred"] == "inferred"
    assert claims[0]["evidence_ids"] == []


def test_invalid_label_defaults_to_inferred() -> None:
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "definitely", "evidence_ids": ["E1"]}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["explicit_or_inferred"] == "inferred"


def test_skips_empty_or_malformed_claims() -> None:
    claims = _normalize_claims(
        [{"text": "  "}, "not-a-dict", {"explicit_or_inferred": "explicit"}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims == []


def test_handles_bad_confidence() -> None:
    claims = _normalize_claims(
        [{"text": "A", "explicit_or_inferred": "unknown", "confidence": "high"}],
        VALID_IDS,
        LABEL_MAP,
    )
    assert claims[0]["confidence"] == 0.0
