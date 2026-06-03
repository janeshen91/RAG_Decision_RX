from __future__ import annotations

from typing import Any


class MockLLMClient:
    """Deterministic fallback client for local MVP testing."""

    def generate_structured_answer(self, *, prompt: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        if not evidence:
            return {
                "answer_summary": "No relevant evidence was retrieved.",
                "rationale_breakdown": {
                    "scientific": "",
                    "business": "",
                    "supply_chain": "",
                    "timeline": "",
                    "regulatory": "",
                    "unknown_or_mixed": "Insufficient evidence to answer confidently.",
                },
                "supporting_evidence": [],
                "claims": [],
                "unknowns": ["No indexed evidence addresses the question."],
                "confidence": 0.1,
                "limitations": ["No matching chunks found in the indexed corpus."],
            }

        top = evidence[0]
        summary = top["snippet"][:350]
        limitations = []
        if len(evidence) < 2:
            limitations.append("Answer is based on limited retrieved context.")

        return {
            "answer_summary": summary,
            "rationale_breakdown": {
                "scientific": summary,
                "business": "Not explicitly stated in retrieved evidence.",
                "supply_chain": "Not explicitly stated in retrieved evidence.",
                "timeline": "Not explicitly stated in retrieved evidence.",
                "regulatory": "Not explicitly stated in retrieved evidence.",
                "unknown_or_mixed": "Some categories are not covered by the evidence.",
            },
            "supporting_evidence": evidence,
            "claims": [
                {
                    "text": summary,
                    "explicit_or_inferred": "explicit",
                    "evidence_ids": ["E1"],
                    "confidence": round(min(0.95, max(0.2, float(top["score"]))), 2),
                }
            ],
            "unknowns": [],
            "confidence": round(min(0.95, max(0.2, float(top["score"]))), 2),
            "limitations": limitations,
        }
