from __future__ import annotations

from src.retrieval.fusion import ReciprocalRankFusion
from src.retrieval.search_repository import SearchRepository
from src.schemas.RetrievalSchemas import RetrievalResult
from src.services.QueryPreparationService import QueryPreparationService
from src.services.RerankingService import RerankingService
from src.stores.llm.providers.CohereProvider import CohereProvider


class RetrievalService:
    """Query rewrite, dense search, lexical search, fusion, and reranking."""

    def __init__(
        self,
        query_preparation: QueryPreparationService | None = None,
        embedding_provider: CohereProvider | None = None,
        repository: SearchRepository | None = None,
        fusion: ReciprocalRankFusion | None = None,
        reranker: RerankingService | None = None,
    ) -> None:
        self.query_preparation = query_preparation or QueryPreparationService()
        self.embedding_provider = embedding_provider or CohereProvider()
        self.repository = repository or SearchRepository()
        self.fusion = fusion or ReciprocalRankFusion()
        self.reranker = reranker or RerankingService()

    def retrieve(
        self,
        user_query: str,
        candidate_limit: int = 8,
        final_limit: int = 5,
        document_id: int | None = None,
    ) -> RetrievalResult:
        normalized_query = user_query.strip()

        if not normalized_query:
            raise ValueError(
                "user_query cannot be empty."
            )

        if candidate_limit < 1 or final_limit < 1:
            raise ValueError(
                "Retrieval limits must be positive."
            )

        prepared = self.query_preparation.prepare(
            normalized_query
        )
        query_embedding = self.embedding_provider.embed_queries(
            [prepared.semantic_query]
        )[0]

        semantic_hits = self.repository.semantic_search(
            query_embedding=query_embedding,
            limit=candidate_limit,
            document_id=document_id,
        )
        keyword_hits = self.repository.keyword_search(
            keyword_query=prepared.keyword_query,
            limit=candidate_limit,
            document_id=document_id,
        )

        hybrid_candidates = self.fusion.fuse(
            semantic_hits=semantic_hits,
            keyword_hits=keyword_hits,
            limit=candidate_limit,
        )
        hybrid_hits = hybrid_candidates[:final_limit]
        reranked_hits = self.reranker.rerank(
            query=prepared.semantic_query,
            candidates=hybrid_candidates,
            top_n=final_limit,
        )

        return RetrievalResult(
            original_query=prepared.rewrite.original_query,
            detected_language=prepared.rewrite.detected_language,
            semantic_query=prepared.semantic_query,
            keyword_query=prepared.keyword_query,
            keyword_terms=prepared.keyword_terms,
            semantic_hits=semantic_hits,
            keyword_hits=keyword_hits,
            hybrid_hits=hybrid_hits,
            reranked_hits=reranked_hits,
        )
