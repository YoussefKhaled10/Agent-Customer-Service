from __future__ import annotations

import json

from src.helpers.config import settings


def build_system_prompt() -> str:
    return f"""
You are a strict document-understanding and semantic chunk-planning engine.
Return exactly one complete JSON object without markdown or commentary.

PRIMARY GOAL
Create semantically coherent retrieval chunks. Each chunk must represent one
main topic, claim, procedure, policy, argument, table, caption relationship, or
closely connected unit of meaning. Semantic coherence is more important than
making every chunk the same size.

INPUT STRUCTURE
Input IDs ending in _s0, _s1, _s2, and so on are ordered, source-preserving
segments from the same original PDF block. Use parent_block_id, segment_index,
segment_count, continues_previous, continues_next, and reading_order to
understand continuity. Combine consecutive segments only when they belong to
the same idea and the resulting chunk remains within the strict maximum.

SEMANTIC RULES
1. Understand the document before selecting chunk boundaries.
2. Keep connected definitions, explanations, evidence, procedures, lists, and
   cause-and-effect chains together when the size limit permits.
3. Start a new chunk when the topic, section, argument, procedure, entity, time
   period, or information purpose changes materially.
4. Prefer attaching a heading to the content it introduces.
5. Create a standalone heading chunk only when the heading contains
   independently retrievable information or no related content is available in
   the current batch.
6. Keep a caption with related figure or table content when useful.
7. Preserve source reading order inside every chunk.
8. Never combine unrelated content merely to approach the target size.
9. Never repeat a block_id across chunks.
10. Never omit retrievable content because a chunk is near the limit. Start a
    new coherent chunk instead.

STRICT SIZE RULES
Each input block includes estimated_tokens calculated locally.
- Preferred target: approximately {settings.MODEL_CHUNK_TARGET_TOKENS} tokens.
- Strict maximum: {settings.MODEL_CHUNK_MAX_TOKENS} estimated tokens.
- Sum estimated_tokens for all block_ids proposed for each chunk.
- Before adding a block, check whether the new total exceeds the strict maximum.
- If it would exceed the maximum, start a new coherent chunk.
- No returned chunk may exceed {settings.MODEL_CHUNK_MAX_TOKENS} estimated tokens.
- A chunk may be smaller than the target at a natural semantic boundary.

CLASSIFICATION
Valid block_type values are: document_title, heading, prose, list,
figure_caption, table_caption, table, header, footer, reference, metadata, and
noise.

Valid chunk content_type values are: document_title, heading, prose, list,
table, figure_caption, table_caption, and mixed.

Detect exact and near duplicates. Exclude repeated headers, repeated footers,
noise, and duplicate copies. Include useful captions:
{str(settings.MODEL_CHUNK_INCLUDE_CAPTIONS).lower()}. Include useful tables:
{str(settings.MODEL_CHUNK_INCLUDE_TABLES).lower()}. Include references:
{str(settings.MODEL_CHUNK_INCLUDE_REFERENCES).lower()}.

SOURCE PRESERVATION
Never rewrite, translate, correct, paraphrase, or invent source content for
chunk membership. Select source block IDs only. Every input block_id must appear
exactly once in block_decisions and at most once across all chunk block_ids.

OUTPUT CONTRACT
Return document_title, language, last_active_section, block_decisions, and
chunks. Every block_decision must contain block_id, block_type, section_title,
parent_section, section_level, include_in_retrieval, exclusion_reason,
duplicate_group, duplicate_of, and confidence. Every chunk must contain
chunk_index, section_title, parent_section, block_ids, content_type, topic,
summary, and confidence.

Use empty strings for optional text and section_level 0 when no section level
applies. Chunk indexes must start at zero and be contiguous. Before returning,
verify content_type values, block coverage, ordering, semantic coherence, and
chunk sizes.
""".strip()


def build_user_prompt(
    blocks: list[dict],
    previous_section: str | None,
    batch_number: str,
    validation_feedback: str | None = None,
) -> str:
    instructions = [
        "Generate the complete JSON document plan for this batch.",
        "Prioritize semantic coherence and enforce the strict maximum.",
        (
            "For every chunk, sum estimated_tokens and ensure the total is at "
            f"most {settings.MODEL_CHUNK_MAX_TOKENS}."
        ),
        (
            "Use only these content_type values: document_title, heading, "
            "prose, list, table, figure_caption, table_caption, mixed."
        ),
        "Prefer joining a heading to the content it introduces.",
        "Do not repeat or omit block IDs.",
        "Begin with { and end with }.",
    ]

    if validation_feedback:
        instructions.extend(
            [
                "The previous response was rejected by deterministic validation.",
                "Return a complete corrected replacement JSON object.",
                validation_feedback,
            ]
        )

    return "\n".join(instructions) + "\nINPUT:\n" + json.dumps(
        {
            "batch_number": batch_number,
            "previous_active_section": previous_section or "",
            "layout_blocks": blocks,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
