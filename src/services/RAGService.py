from __future__ import annotations

from src.schemas.AnswerSchemas import RAGResponse
from src.services.AnswerGenerationService import AnswerGenerationService
from src.services.ContextBuilderService import ContextBuilderService
from src.services.RetrievalService import RetrievalService


class RAGService:
    """Run retrieval, reranking, context building, and grounded generation."""

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        context_builder: ContextBuilderService | None = None,
        answer_generator: AnswerGenerationService | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()
        self.context_builder = context_builder or ContextBuilderService()
        self.answer_generator = answer_generator or AnswerGenerationService()

    def answer(
        self,
        query: str,
        *,
        document_id: int | None = None,
        candidate_limit: int = 8,
        retrieval_top_k: int = 5,
        context_max_chunks: int = 3,
        context_token_budget: int = 1800,
        minimum_context_score: float | None = None,
    ) -> RAGResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty.")

        retrieval = self.retrieval_service.retrieve(
            normalized_query,
            candidate_limit=candidate_limit,
            final_limit=retrieval_top_k,
            document_id=document_id,
        )
        context = self.context_builder.build(
            retrieval.reranked_hits,
            token_budget=context_token_budget,
            max_chunks=context_max_chunks,
            minimum_score=minimum_context_score,
        )
        generated = self.answer_generator.generate(
            query=retrieval.original_query,
            detected_language=retrieval.detected_language,
            context=context,
        )
        return RAGResponse(
            query=retrieval.original_query,
            detected_language=retrieval.detected_language,
            answer=generated,
            context=context,
        )
