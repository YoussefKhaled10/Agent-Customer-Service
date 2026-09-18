from __future__ import annotations

from dataclasses import replace

import cohere

from src.helpers.config import settings
from src.schemas.RetrievalSchemas import RetrievalHit


class RerankingError(Exception):
    """Raised when retrieval candidates cannot be reranked."""


class RerankingService:
    """Rerank retrieval candidates with Cohere without changing retrieval scores."""

    def __init__(
        self,
        client: cohere.ClientV2 | None = None,
        model: str | None = None,
    ) -> None:
        if client is None and not settings.COHERE_API_KEY:
            raise RerankingError("COHERE_API_KEY is required for reranking.")

        self.client = client or cohere.ClientV2(
            api_key=settings.COHERE_API_KEY
        )
        self.model = model or getattr(
            settings,
            "RERANK_MODEL",
            "rerank-v3.5",
        )

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        top_n: int = 3,
    ) -> list[RetrievalHit]:
        normalized_query = query.strip()
        if not normalized_query:
            raise RerankingError("Reranking query cannot be empty.")
        if top_n < 1:
            raise ValueError("top_n must be positive.")
        if not candidates:
            return []

        documents = [self._document_text(hit) for hit in candidates]
        requested_top_n = min(top_n, len(candidates))

        try:
            response = self.client.rerank(
                model=self.model,
                query=normalized_query,
                documents=documents,
                top_n=requested_top_n,
            )
        except Exception as error:
            raise RerankingError(
                f"Cohere reranking failed: {error}"
            ) from error

        output: list[RetrievalHit] = []
        seen_indexes: set[int] = set()

        for rank, result in enumerate(response.results, start=1):
            index = int(result.index)
            if index < 0 or index >= len(candidates):
                raise RerankingError(
                    f"Cohere returned invalid candidate index: {index}."
                )
            if index in seen_indexes:
                raise RerankingError(
                    f"Cohere returned duplicate candidate index: {index}."
                )

            seen_indexes.add(index)
            output.append(
                replace(
                    candidates[index],
                    rerank_score=float(result.relevance_score),
                    rerank_rank=rank,
                )
            )

        return output

    @staticmethod
    def _document_text(hit: RetrievalHit) -> str:
        metadata = hit.metadata or {}
        parts = [
            f"Title: {metadata.get('document_title', '')}",
            f"Section: {metadata.get('section_title', '')}",
            f"Topic: {metadata.get('topic', '')}",
            f"Summary: {metadata.get('summary', '')}",
            f"Content type: {metadata.get('content_type', '')}",
            f"Content: {hit.content}",
        ]
        return "\n".join(part for part in parts if part.split(":", 1)[1].strip())
