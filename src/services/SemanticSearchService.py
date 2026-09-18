from __future__ import annotations


class SemanticSearchService:
    """Coordinate query embedding and vector similarity search."""

    def __init__(self, embedding_provider, repository) -> None:
        self.embedding_provider = embedding_provider
        self.repository = repository

    def search(self, query: str, limit: int = 8, document_id: int | None = None):
        vector = self.embedding_provider.embed_queries([query])[0]
        return self.repository.semantic_search(
            query_vector=vector,
            limit=limit,
            document_id=document_id,
        )
