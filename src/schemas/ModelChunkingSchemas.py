from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BlockType = Literal[
    "document_title",
    "heading",
    "prose",
    "list",
    "figure_caption",
    "table_caption",
    "table",
    "header",
    "footer",
    "reference",
    "metadata",
    "noise",
]

ContentType = Literal[
    "document_title",
    "heading",
    "prose",
    "list",
    "table",
    "figure_caption",
    "table_caption",
    "mixed",
]


class LayoutSpan(BaseModel):
    text: str
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    bbox: tuple[float, float, float, float]


class LayoutBlock(BaseModel):
    block_id: str
    page_number: int
    block_index: int
    reading_order: int
    text: str
    bbox: tuple[float, float, float, float]
    page_width: float
    page_height: float
    page_rotation: int = 0
    distance_from_previous: float | None = None
    average_font_size: float = 0.0
    maximum_font_size: float = 0.0
    spans: list[LayoutSpan] = Field(default_factory=list)
    parent_block_id: str | None = None
    segment_index: int = 0
    segment_count: int = 1
    continues_previous: bool = False
    continues_next: bool = False


class BlockDecision(BaseModel):
    block_id: str
    block_type: BlockType
    section_title: str | None = None
    parent_section: str | None = None
    section_level: int | None = None
    starts_new_section: bool = False
    continuation_of_previous: bool = False
    continues_in_next_batch: bool = False
    include_in_retrieval: bool = True
    exclusion_reason: str | None = None
    duplicate_group: str | None = None
    duplicate_of: str | None = None
    confidence: float = 1.0


class ChunkDecision(BaseModel):
    chunk_index: int
    section_title: str | None = None
    parent_section: str | None = None
    block_ids: list[str]
    content_type: ContentType
    topic: str
    summary: str
    confidence: float = 1.0


class ModelDocumentPlan(BaseModel):
    document_title: str | None = None
    language: str = "unknown"
    last_active_section: str | None = None
    continues_to_next_batch: bool = False
    block_decisions: list[BlockDecision]
    chunks: list[ChunkDecision]


class FinalChunk(BaseModel):
    chunk_index: int
    content: str
    token_count: int
    page_start: int
    page_end: int
    block_ids: list[str]
    block_indexes: list[int]
    section_title: str | None = None
    parent_section: str | None = None
    content_type: ContentType
    topic: str
    summary: str
    confidence: float = 1.0
    chunking_method: str = "model_hierarchical_v3"
    chunking_provider: str | None = None
    chunking_model: str | None = None
    planner_window: int | None = None
    planner_concurrency: int | None = None
