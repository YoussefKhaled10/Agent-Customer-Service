from __future__ import annotations

import re

from src.helpers.config import settings
from src.schemas.ModelChunkingSchemas import LayoutBlock
from src.ingestion.token_counter import TokenCounter


class LayoutBlockRefiner:
    """Split oversized raw blocks into ordered, source-preserving sub-blocks."""

    _sentence_boundary = re.compile(
        r"(?<=[.!?])(?=\s+)|(?<=[。！？])|(?=\n{2,})",
        re.UNICODE,
    )

    def __init__(
        self,
        target_tokens: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.target_tokens = target_tokens or settings.LAYOUT_BLOCK_TARGET_TOKENS
        self.max_tokens = max_tokens or settings.LAYOUT_BLOCK_MAX_TOKENS
        if self.target_tokens < 1 or self.max_tokens < self.target_tokens:
            raise ValueError("Invalid layout block refinement settings.")

    def refine(self, blocks: list[LayoutBlock]) -> list[LayoutBlock]:
        refined: list[LayoutBlock] = []
        reading_order = 0

        for block in blocks:
            parts = self._split_text(block.text)
            part_count = len(parts)

            for part_index, part in enumerate(parts):
                refined.append(
                    block.model_copy(
                        update={
                            "block_id": (
                                block.block_id
                                if part_count == 1
                                else f"{block.block_id}_s{part_index}"
                            ),
                            "reading_order": reading_order,
                            "text": part,
                            "parent_block_id": block.block_id,
                            "segment_index": part_index,
                            "segment_count": part_count,
                            "continues_previous": part_index > 0,
                            "continues_next": part_index < part_count - 1,
                        }
                    )
                )
                reading_order += 1

        return refined

    def _split_text(self, text: str) -> list[str]:
        if not text or TokenCounter.estimate(text) <= self.max_tokens:
            return [text]

        boundaries = [0]
        boundaries.extend(match.start() for match in self._sentence_boundary.finditer(text))
        boundaries.append(len(text))
        boundaries = sorted(set(boundaries))

        units = [
            text[boundaries[index] : boundaries[index + 1]]
            for index in range(len(boundaries) - 1)
            if boundaries[index] < boundaries[index + 1]
        ]

        safe_units: list[str] = []
        for unit in units:
            if TokenCounter.estimate(unit) <= self.max_tokens:
                safe_units.append(unit)
            else:
                safe_units.extend(self._split_long_unit(unit))

        parts: list[str] = []
        current = ""

        for unit in safe_units:
            candidate = current + unit
            if current and TokenCounter.estimate(candidate) > self.target_tokens:
                parts.append(current)
                current = unit
            else:
                current = candidate

        if current:
            parts.append(current)

        if "".join(parts) != text:
            raise ValueError("Layout refinement changed or lost source text.")
        if any(TokenCounter.estimate(part) > self.max_tokens for part in parts):
            raise ValueError("Layout refinement produced an oversized sub-block.")

        return parts

    def _split_long_unit(self, text: str) -> list[str]:
        parts: list[str] = []
        start = 0

        while start < len(text):
            end = self._largest_safe_end(text, start)
            if end <= start:
                raise ValueError("Unable to split an oversized source unit safely.")
            parts.append(text[start:end])
            start = end

        return parts

    def _largest_safe_end(self, text: str, start: int) -> int:
        low = start + 1
        high = len(text)
        best = low

        while low <= high:
            middle = (low + high) // 2
            if TokenCounter.estimate(text[start:middle]) <= self.max_tokens:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        if best >= len(text):
            return len(text)

        whitespace = max(
            text.rfind(" ", start, best),
            text.rfind("\n", start, best),
            text.rfind("\t", start, best),
        )
        return whitespace + 1 if whitespace > start else best
