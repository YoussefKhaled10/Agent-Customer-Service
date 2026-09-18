from __future__ import annotations

import json
from typing import Any

from groq import Groq

from src.helpers.config import settings
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class GroqProviderError(Exception):
    """Raised when Groq cannot generate a valid structured response."""


class GroqProvider(AnswerProviderInterface):
    def __init__(
        self,
        client: Groq | None = None,
        model: str | None = None,
    ) -> None:
        if client is None and not settings.GROQ_API_KEY:
            raise GroqProviderError("GROQ_API_KEY is missing from src/.env.")
        self.client = client or Groq(api_key=settings.GROQ_API_KEY)
        self.model = model or settings.GROQ_ANSWER_MODEL

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        schema_instruction = json.dumps(json_schema, ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    "Return a valid JSON object only. It must follow this JSON Schema:\n"
                    f"{schema_instruction}"
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise GroqProviderError("Groq returned no content.")
            payload = json.loads(content)
        except GroqProviderError:
            raise
        except Exception as error:
            raise GroqProviderError(f"Groq generation failed: {error}") from error

        if not isinstance(payload, dict):
            raise GroqProviderError("Groq response must be a JSON object.")
        return payload
