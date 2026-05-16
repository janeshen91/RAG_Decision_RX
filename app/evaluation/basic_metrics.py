from __future__ import annotations


def has_minimum_evidence(supporting_evidence: list[dict], minimum: int = 1) -> bool:
    return len(supporting_evidence) >= minimum
