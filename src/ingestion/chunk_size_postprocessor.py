from __future__ import annotations

from src.schemas.ModelChunkingSchemas import LayoutBlock
from src.ingestion.token_counter import TokenCounter


class ChunkSizePostProcessor:
    """Split one Cohere-planned block group into ordered groups under a hard limit."""

    def __init__(self, max_tokens: int) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive.")
        self.max_tokens = max_tokens

    def split(self, blocks: list[LayoutBlock]) -> list[list[LayoutBlock]]:
        if not blocks:
            return []

        ordered = sorted(blocks, key=lambda block: block.reading_order)
        groups: list[list[LayoutBlock]] = []
        current: list[LayoutBlock] = []

        for block in ordered:
            block_tokens = TokenCounter.estimate(block.text)
            if block_tokens > self.max_tokens:
                raise ValueError(
                    f"Input block {block.block_id} exceeds the hard chunk limit "
                    f"({block_tokens} > {self.max_tokens})."
                )

            candidate = current + [block]
            candidate_text = "\n\n".join(item.text.strip() for item in candidate)
            if current and TokenCounter.estimate(candidate_text) > self.max_tokens:
                groups.append(current)
                current = [block]
            else:
                current = candidate

        if current:
            groups.append(current)

        return groups
