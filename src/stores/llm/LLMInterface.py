from abc import ABC, abstractmethod
from collections.abc import Sequence


class LLMInterface(ABC):
    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for documents stored in the vector database."""

    @abstractmethod
    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for search queries."""
