from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AnswerProviderInterface(ABC):
    """Provider-independent interface for structured answer generation."""

    @abstractmethod
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate and return a JSON object matching the requested schema."""
