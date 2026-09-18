from collections.abc import Sequence
from math import sqrt

import cohere

from src.helpers.config import settings
from src.exceptions.IngestionExceptions import EmbeddingError
from src.stores.llm.LLMInterface import LLMInterface


class CohereProvider(LLMInterface):
    def __init__(self, client: cohere.ClientV2 | None = None) -> None:
        if not settings.COHERE_API_KEY and client is None:
            raise EmbeddingError("COHERE_API_KEY is missing from src/.env.")
        self.client = client or cohere.ClientV2(api_key=settings.COHERE_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self.normalize = settings.EMBEDDING_NORMALIZE

    @staticmethod
    def _normalize_vector(vector: list[float]) -> list[float]:
        magnitude = sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]

    def _validate_vectors(self, vectors: list[list[float]]) -> list[list[float]]:
        for vector in vectors:
            if len(vector) != self.dimension:
                raise EmbeddingError(
                    f"Expected {self.dimension} dimensions, received {len(vector)}."
                )
        return [self._normalize_vector(v) for v in vectors] if self.normalize else vectors

    def _embed(self, texts: Sequence[str], input_type: str) -> list[list[float]]:
        cleaned = [text.strip() for text in texts]
        if not cleaned or any(not text for text in cleaned):
            raise EmbeddingError("Embedding input cannot be empty.")
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(cleaned), self.batch_size):
                response = self.client.embed(
                    texts=cleaned[start:start + self.batch_size],
                    model=self.model,
                    input_type=input_type,
                    embedding_types=[settings.EMBEDDING_TYPE],
                )
                vectors.extend([list(vector) for vector in response.embeddings.float])
        except Exception as error:
            raise EmbeddingError(f"Cohere embedding generation failed: {error}") from error
        return self._validate_vectors(vectors)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, settings.EMBEDDING_DOCUMENT_INPUT_TYPE)

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, settings.EMBEDDING_QUERY_INPUT_TYPE)
