from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from src.helpers.config import settings
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class GeminiProviderError(Exception):
    """Raised when Gemini cannot generate a valid structured response."""


class GeminiProvider(AnswerProviderInterface):
    def __init__(
        self,
        client: genai.Client | None = None,
        model: str | None = None,
    ) -> None:
        if client is None and not settings.GEMINI_API_KEY:
            raise GeminiProviderError("GEMINI_API_KEY is missing from src/.env.")
        self.client = client or genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = model or settings.GEMINI_ANSWER_MODEL

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                    response_mime_type="application/json",
                    response_json_schema=json_schema,
                ),
            )
            if not response.text:
                raise GeminiProviderError("Gemini returned no content.")
            payload = json.loads(response.text)
        except GeminiProviderError:
            raise
        except Exception as error:
            raise GeminiProviderError(f"Gemini generation failed: {error}") from error

        if not isinstance(payload, dict):
            raise GeminiProviderError("Gemini response must be a JSON object.")
        return payload
