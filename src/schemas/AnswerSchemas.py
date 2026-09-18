from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.ContextSchemas import BuiltContext


@dataclass(frozen=True, slots=True)
class AnswerSource:
    source_id: str
    document_id: int
    chunk_id: int
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    document_title: str | None = None
    file_name: str | None = None
    section_title: str | None = None
    topic: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    answer: str
    language: str
    answerable: bool
    cited_source_ids: list[str] = field(default_factory=list)
    sources: list[AnswerSource] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RAGResponse:
    query: str
    detected_language: str
    answer: GeneratedAnswer
    context: BuiltContext
