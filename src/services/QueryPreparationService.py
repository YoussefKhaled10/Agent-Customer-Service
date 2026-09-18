from __future__ import annotations

from src.retrieval.query_rewriter import QueryRewriter
from src.schemas.RetrievalSchemas import RetrievalQueries


class QueryPreparationService:
    def __init__(self, rewriter: QueryRewriter | None = None) -> None:
        self.rewriter = rewriter or QueryRewriter()

    def prepare(self, user_query: str) -> RetrievalQueries:
        rewrite = self.rewriter.rewrite(user_query)
        return RetrievalQueries(
            semantic_query=rewrite.semantic_query,
            keyword_query=rewrite.keyword_query,
            keyword_terms=rewrite.keywords,
            rewrite=rewrite,
        )
