from __future__ import annotations

from typing import Any

from src.schemas.AnswerSchemas import RAGResponse
from src.schemas.ToolSchemas import ToolDefinition
from src.services.RAGService import RAGService
from src.tools.ToolInterface import ToolInterface


class KnowledgeRAGTool(ToolInterface):
    """Expose the completed RAG pipeline as a read-only agent tool."""

    def __init__(self, rag_service: RAGService | None = None) -> None:
        self.rag_service = rag_service or RAGService()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="knowledge_rag",
            description=(
                "Answer questions using indexed PharmaCare knowledge documents. "
                "Use this tool for policy, treatment, product-information, and "
                "other knowledge questions that must be grounded in documents."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "description": "The user's complete knowledge question.",
                    },
                    "document_id": {
                        "type": "integer",
                        "minimum": 1,
                        "description": (
                            "Optional knowledge document ID used to restrict retrieval."
                        ),
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("knowledge", "rag", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        query = str(arguments["query"]).strip()
        document_id = arguments.get("document_id")

        response = self.rag_service.answer(
            query,
            document_id=document_id,
        )
        return self._serialize_response(response)

    @classmethod
    def _serialize_response(cls, response: RAGResponse) -> dict[str, Any]:
        answer = str(response.answer.answer or "").strip()
        answerable = bool(response.answer.answerable and answer)
        cited_source_ids = list(response.answer.cited_source_ids)
        return {
            "query": response.query,
            "detected_language": response.detected_language,
            "answer": answer,
            "answerable": answerable,
            "grounded": answerable and bool(cited_source_ids),
            "cited_source_ids": cited_source_ids,
            "sources": [
                {
                    "source_id": source.source_id,
                    "document_id": source.document_id,
                    "chunk_id": source.chunk_id,
                    "chunk_index": source.chunk_index,
                    "pages": [source.page_start, source.page_end],
                    "document_title": source.document_title,
                    "file_name": source.file_name,
                    "section_title": source.section_title,
                    "topic": source.topic,
                }
                for source in response.answer.sources
            ],
            "context": {
                "selected_count": response.context.selected_count,
                "total_tokens": response.context.total_tokens,
                "token_budget": response.context.token_budget,
            },
        }
