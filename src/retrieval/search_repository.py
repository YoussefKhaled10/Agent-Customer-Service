from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from src.models.Database import database_session
from src.schemas.RetrievalSchemas import SearchHit


class SearchRepository:
    """PostgreSQL/pgvector search adapter for indexed knowledge chunks."""

    def semantic_search(
        self,
        query_embedding: list[float],
        limit: int,
        document_id: int | None = None,
    ) -> list[SearchHit]:
        statement = text(
            """
            SELECT
                kc.id AS chunk_id,
                kc.document_id,
                kc.chunk_index,
                kc.content,
                kc.token_count,
                kc.chunk_metadata,
                1 - (kc.embedding <=> CAST(:query_embedding AS vector)) AS score
            FROM knowledge_chunks AS kc
            JOIN knowledge_documents AS kd ON kd.id = kc.document_id
            WHERE kd.is_active = TRUE
              AND kd.index_status = 'indexed'
              AND (CAST(:document_id AS BIGINT) IS NULL OR kc.document_id = CAST(:document_id AS BIGINT))
            ORDER BY kc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        )
        parameters = {
            "query_embedding": self._vector_literal(query_embedding),
            "document_id": document_id,
            "limit": limit,
        }
        with database_session() as session:
            rows = session.execute(statement, parameters).mappings().all()
        return [self._row_to_hit(row, semantic=True) for row in rows]

    def keyword_search(
        self,
        keyword_query: str,
        limit: int,
        document_id: int | None = None,
    ) -> list[SearchHit]:
        statement = text(
            """
            WITH searchable AS (
                SELECT
                    kc.id AS chunk_id,
                    kc.document_id,
                    kc.chunk_index,
                    kc.content,
                    kc.token_count,
                    kc.chunk_metadata,
                    setweight(to_tsvector('english', COALESCE(kc.content, '')), 'A')
                    || setweight(
                        to_tsvector(
                            'english',
                            COALESCE(kc.chunk_metadata ->> 'topic', '') || ' ' ||
                            COALESCE(kc.chunk_metadata ->> 'summary', '') || ' ' ||
                            COALESCE(kc.chunk_metadata ->> 'section_title', '')
                        ),
                        'B'
                    ) AS search_vector
                FROM knowledge_chunks AS kc
                JOIN knowledge_documents AS kd ON kd.id = kc.document_id
                WHERE kd.is_active = TRUE
                  AND kd.index_status = 'indexed'
                  AND (CAST(:document_id AS BIGINT) IS NULL OR kc.document_id = CAST(:document_id AS BIGINT))
            ), query AS (
                SELECT websearch_to_tsquery('english', :keyword_query) AS value
            )
            SELECT
                searchable.chunk_id,
                searchable.document_id,
                searchable.chunk_index,
                searchable.content,
                searchable.token_count,
                searchable.chunk_metadata,
                ts_rank_cd(searchable.search_vector, query.value) AS score
            FROM searchable, query
            WHERE searchable.search_vector @@ query.value
            ORDER BY score DESC, searchable.chunk_id
            LIMIT :limit
            """
        )
        with database_session() as session:
            rows = session.execute(
                statement,
                {
                    "keyword_query": keyword_query,
                    "document_id": document_id,
                    "limit": limit,
                },
            ).mappings().all()
        return [self._row_to_hit(row, semantic=False) for row in rows]

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(format(value, ".10g") for value in vector) + "]"

    @staticmethod
    def _metadata(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @classmethod
    def _row_to_hit(cls, row: Any, semantic: bool) -> SearchHit:
        score = float(row["score"] or 0.0)
        return SearchHit(
            chunk_id=int(row["chunk_id"]),
            document_id=int(row["document_id"]),
            chunk_index=int(row["chunk_index"]),
            content=row["content"],
            token_count=int(row["token_count"]),
            metadata=cls._metadata(row["chunk_metadata"]),
            semantic_score=score if semantic else None,
            keyword_score=None if semantic else score,
        )
