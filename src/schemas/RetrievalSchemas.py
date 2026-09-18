from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RewrittenQuery:
    original_query: str
    detected_language: str
    normalized_query: str
    semantic_query: str
    keyword_query: str
    keywords: list[str] = field(default_factory=list)
    was_rewritten: bool = False


@dataclass(frozen=True)
class RetrievalQueries:
    semantic_query: str
    keyword_query: str
    keyword_terms: list[str]
    rewrite: RewrittenQuery


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    rerank_score: float | None = None
    rerank_rank: int | None = None


SearchHit = RetrievalHit


@dataclass(frozen=True)
class RetrievalResult:
    original_query: str
    detected_language: str
    semantic_query: str
    keyword_query: str
    keyword_terms: list[str]
    semantic_hits: list[RetrievalHit]
    keyword_hits: list[RetrievalHit]
    hybrid_hits: list[RetrievalHit]
    reranked_hits: list[RetrievalHit] = field(default_factory=list)
