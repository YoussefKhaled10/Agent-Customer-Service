from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextItem:
    source_id: str
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    page_start: int | None = None
    page_end: int | None = None
    document_title: str | None = None
    file_name: str | None = None
    section_title: str | None = None
    topic: str | None = None
    content_type: str | None = None
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BuiltContext:
    text: str
    items: list[ContextItem]
    total_tokens: int
    token_budget: int
    candidate_count: int
    selected_count: int
    skipped_duplicate_count: int = 0
    skipped_budget_count: int = 0
    skipped_score_count: int = 0
