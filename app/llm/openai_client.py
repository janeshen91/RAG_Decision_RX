from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


class OpenAILLMClient:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_structured_answer(self, *, prompt: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON using keys: answer_summary, rationale_breakdown, "
                        "supporting_evidence, claims, unknowns, confidence, limitations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        text = response.choices[0].message.content or "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "answer_summary": "LLM returned non-JSON output.",
                "rationale_breakdown": {
                    "scientific": "",
                    "business": "",
                    "supply_chain": "",
                    "timeline": "",
                    "regulatory": "",
                    "unknown_or_mixed": "Unable to parse LLM response.",
                },
                "supporting_evidence": evidence,
                "claims": [],
                "unknowns": [],
                "confidence": 0.2,
                "limitations": ["Response parsing failed."],
            }
