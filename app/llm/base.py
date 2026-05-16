from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    def generate_structured_answer(self, *, prompt: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        ...
