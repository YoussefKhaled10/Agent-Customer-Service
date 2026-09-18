from src.helpers.config import settings
from src.stores.llm.LLMEnums import LLMProvider
from src.stores.llm.LLMInterface import LLMInterface
from src.stores.llm.providers.CohereProvider import (
    CohereProvider,
)


class LLMFactory:
    @staticmethod
    def create(
        provider: str | LLMProvider | None = None,
    ) -> LLMInterface:
        selected = LLMProvider(
            provider or settings.EMBEDDING_BACKEND
        )

        if selected == LLMProvider.COHERE:
            return CohereProvider()

        raise ValueError(
            "Unsupported embedding provider: "
            f"{selected}"
        )