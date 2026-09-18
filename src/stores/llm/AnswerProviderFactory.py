from __future__ import annotations

from src.helpers.config import settings
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class AnswerProviderFactory:
    @staticmethod
    def create(
        provider: str | None = None,
        *,
        model: str | None = None,
    ) -> AnswerProviderInterface:
        selected = (provider or settings.ANSWER_PROVIDER).strip().casefold()

        if selected == "groq":
            from src.stores.llm.providers.GroqProvider import GroqProvider
            return GroqProvider(model=model)

        if selected == "gemini":
            from src.stores.llm.providers.GeminiProvider import GeminiProvider
            return GeminiProvider(model=model)

        raise ValueError(f"Unsupported answer provider: {selected}")
