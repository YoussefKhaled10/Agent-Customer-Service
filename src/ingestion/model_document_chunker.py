from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from typing import Any

from src.helpers.config import settings
from src.ingestion.chunk_size_postprocessor import ChunkSizePostProcessor
from src.exceptions.IngestionExceptions import ModelChunkingError
from src.ingestion.model_chunking_prompt import build_system_prompt, build_user_prompt
from src.schemas.ModelChunkingSchemas import (
    BlockDecision,
    FinalChunk,
    LayoutBlock,
    ModelDocumentPlan,
)
from src.ingestion.token_counter import TokenCounter
from src.stores.llm.AnswerProviderFactory import AnswerProviderFactory
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class ModelGenerationError(ModelChunkingError):
    """Raised when the configured planner cannot generate a usable batch."""


CohereGenerationError = ModelGenerationError


class ModelDocumentChunker:
    def __init__(
        self,
        provider: AnswerProviderInterface | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        # api_key and base_url remain accepted for compatibility with older callers.
        del api_key, base_url
        self.model = model or settings.DOCUMENT_CHUNKING_MODEL
        self.provider = provider or AnswerProviderFactory.create(
            settings.DOCUMENT_CHUNKING_PROVIDER,
            model=self.model,
        )
        self.timeout_seconds = settings.MODEL_CHUNK_TIMEOUT_SECONDS
        self.max_retries = settings.MODEL_CHUNK_MAX_RETRIES
        self.max_response_attempts = max(1, self.max_retries + 1)
        self.max_plan_attempts = max(1, self.max_retries + 1)
        self.max_blocks = settings.MODEL_CHUNK_MAX_BLOCKS_PER_REQUEST
        self.overlap = settings.MODEL_CHUNK_BATCH_OVERLAP_BLOCKS
        self.planner_window = settings.MODEL_CHUNK_PLANNER_WINDOW
        self.planner_concurrency = settings.MODEL_CHUNK_PLANNER_CONCURRENCY
        self.minimum_split_size = 3
        self.last_run_diagnostics: dict[str, Any] = {}

        if self.max_blocks < 1 or self.overlap < 0 or self.overlap >= self.max_blocks:
            raise ModelChunkingError("Invalid model batching settings.")
        if self.planner_window < 1:
            raise ModelChunkingError("MODEL_CHUNK_PLANNER_WINDOW must be positive.")
        if self.planner_concurrency < 1:
            raise ModelChunkingError("MODEL_CHUNK_PLANNER_CONCURRENCY must be positive.")
        if self.planner_concurrency > self.planner_window:
            raise ModelChunkingError(
                "MODEL_CHUNK_PLANNER_CONCURRENCY cannot exceed MODEL_CHUNK_PLANNER_WINDOW."
            )

    def chunk(self, blocks: list[LayoutBlock]) -> list[FinalChunk]:
        if not blocks:
            return []

        final: list[FinalChunk] = []
        processed_ids: set[str] = set()
        duplicate_groups: set[str] = set()
        previous_section: str | None = None
        decision_by_id: dict[str, BlockDecision] = {}
        batches = self._create_batches(blocks)

        # A planner window limits buffered batches. Batches in each window are
        # planned concurrently, then materialized strictly in document order.
        for window_start in range(0, len(batches), self.planner_window):
            window = batches[window_start : window_start + self.planner_window]
            planned: dict[int, list[tuple[ModelDocumentPlan, list[LayoutBlock]]]] = {}
            with ThreadPoolExecutor(max_workers=self.planner_concurrency) as pool:
                futures = {
                    pool.submit(
                        self._plan_batch_with_fallback,
                        batch,
                        previous_section,
                        str(window_start + index + 1),
                    ): index
                    for index, batch in enumerate(window)
                }
                for future in as_completed(futures):
                    planned[futures[future]] = future.result()

            for index in range(len(window)):
                for plan, planned_blocks in planned[index]:
                    for decision in plan.block_decisions:
                        decision_by_id.setdefault(decision.block_id, decision)
                    final.extend(
                        self._materialize(
                            plan,
                            planned_blocks,
                            processed_ids,
                            duplicate_groups,
                            len(final),
                        )
                    )
                    previous_section = plan.last_active_section or previous_section

        final = self._propagate_missing_sections(final)
        final = self._merge_tiny_chunks(final)
        final = self._reindex_chunks(final)
        self._validate_final(final)
        self.last_run_diagnostics = self._build_diagnostics(
            blocks=blocks,
            decisions=decision_by_id,
            chunks=final,
        )
        return final

    def _create_batches(self, blocks: list[LayoutBlock]) -> list[list[LayoutBlock]]:
        if len(blocks) <= self.max_blocks:
            return [blocks]

        step = self.max_blocks - self.overlap
        batches: list[list[LayoutBlock]] = []
        for start in range(0, len(blocks), step):
            batch = blocks[start : start + self.max_blocks]
            if batch:
                batches.append(batch)
            if start + self.max_blocks >= len(blocks):
                break
        return batches

    def _plan_batch_with_fallback(
        self,
        blocks: list[LayoutBlock],
        previous_section: str | None,
        batch_label: str,
    ) -> list[tuple[ModelDocumentPlan, list[LayoutBlock]]]:
        try:
            plan = self._request_valid_plan(blocks, previous_section, batch_label)
            return [(plan, blocks)]
        except ModelGenerationError:
            if len(blocks) <= self.minimum_split_size:
                raise

            midpoint = len(blocks) // 2
            left = blocks[:midpoint]
            right = blocks[midpoint:]

            left_plans = self._plan_batch_with_fallback(
                left,
                previous_section,
                f"{batch_label}.1",
            )
            next_section = left_plans[-1][0].last_active_section or previous_section
            right_plans = self._plan_batch_with_fallback(
                right,
                next_section,
                f"{batch_label}.2",
            )
            return left_plans + right_plans

    def _request_valid_plan(
        self,
        blocks: list[LayoutBlock],
        previous_section: str | None,
        batch_label: str,
    ) -> ModelDocumentPlan:
        feedback: str | None = None
        last_error: ModelChunkingError | None = None

        for attempt in range(1, self.max_plan_attempts + 1):
            plan = self._request_parseable_plan(
                blocks,
                previous_section,
                batch_label,
                feedback,
            )
            try:
                self._validate_plan(plan, blocks)
                return plan
            except ModelChunkingError as error:
                last_error = error
                if attempt >= self.max_plan_attempts:
                    break
                feedback = (
                    f"Plan validation attempt {attempt} failed: {error}. "
                    "Rebuild every decision and chunk in a complete replacement plan."
                )

        raise ModelChunkingError(
            "Document planner failed to produce a valid document plan after "
            f"{self.max_plan_attempts} attempts. Last error: {last_error}"
        )

    def _request_parseable_plan(
        self,
        blocks: list[LayoutBlock],
        previous_section: str | None,
        batch_label: str,
        validation_feedback: str | None,
    ) -> ModelDocumentPlan:
        feedback = validation_feedback
        last_error: ModelChunkingError | None = None

        for attempt in range(1, self.max_response_attempts + 1):
            try:
                response = self._request_response(
                    blocks,
                    previous_section,
                    batch_label,
                    feedback,
                )
                return self._parse_response(response)
            except ModelGenerationError:
                raise
            except ModelChunkingError as error:
                last_error = error
                if attempt >= self.max_response_attempts:
                    break
                feedback = (
                    f"Structured response attempt {attempt} failed: {error}. "
                    "Return the entire JSON object again, not a fragment."
                )

        raise CohereGenerationError(
            "Document planner failed to return parseable JSON after "
            f"{self.max_response_attempts} attempts. Last error: {last_error}"
        )

    def _request_response(
        self,
        blocks: list[LayoutBlock],
        previous_section: str | None,
        batch_label: str,
        validation_feedback: str | None,
    ) -> dict[str, Any]:
        try:
            return self.provider.generate_json(
                system_prompt=build_system_prompt(),
                user_prompt=build_user_prompt(
                    self._compact_blocks(blocks),
                    previous_section,
                    batch_label,
                    validation_feedback,
                ),
                json_schema=ModelDocumentPlan.model_json_schema(),
            )
        except Exception as error:
            raise ModelGenerationError(
                f"Document planner generation failed for batch {batch_label}: {error}"
            ) from error

    @staticmethod
    def _compact_blocks(blocks: list[LayoutBlock]) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for block in blocks:
            compact.append(
                {
                    "block_id": block.block_id,
                    "page_number": block.page_number,
                    "reading_order": block.reading_order,
                    "text": block.text,
                    "estimated_tokens": TokenCounter.estimate(block.text),
                    "estimated_tokens": TokenCounter.estimate(
                            block.text
                    ),
                    "bbox": [round(value, 1) for value in block.bbox],
                    "page_size": [round(block.page_width, 1), round(block.page_height, 1)],
                    "page_rotation": block.page_rotation,
                    "distance_from_previous": (
                        None
                        if block.distance_from_previous is None
                        else round(block.distance_from_previous, 1)
                    ),
                    "average_font_size": round(block.average_font_size, 1),
                    "maximum_font_size": round(block.maximum_font_size, 1),
                    "font_names": sorted(
                        {span.font_name for span in block.spans if span.font_name}
                    ),
                    "has_bold": any(span.is_bold for span in block.spans),
                    "has_italic": any(span.is_italic for span in block.spans),
                }
            )
        return compact

    @classmethod
    def _parse_response(cls, response: Any) -> ModelDocumentPlan:
        if isinstance(response, dict):
            raw_plan = response
        else:
            try:
                response_data = response.json()
            except (AttributeError, ValueError) as error:
                raise ModelChunkingError("Planner returned a non-JSON response.") from error
            message = response_data.get("message")
            items = message.get("content") if isinstance(message, dict) else None
            text = "".join(
                item.get("text", "")
                for item in (items or [])
                if isinstance(item, dict) and item.get("type") == "text"
            ).strip()
            if not text:
                raise ModelChunkingError("Planner response contains no JSON content.")
            try:
                raw_plan = json.loads(text)
            except json.JSONDecodeError as error:
                raise ModelChunkingError("Planner returned malformed JSON.") from error

        normalized = cls._normalize_plan(raw_plan)
        try:
            return ModelDocumentPlan.model_validate(normalized)
        except Exception as error:
            raise ModelChunkingError(
                f"Planner JSON does not match ModelDocumentPlan: {error}"
            ) from error

    @staticmethod
    def _normalize_plan(raw_plan: Any) -> dict[str, Any]:
        if not isinstance(raw_plan, dict):
            raise ModelChunkingError("Document planner plan root must be a JSON object.")

        plan = dict(raw_plan)
        plan.setdefault("document_title", None)
        plan.setdefault("language", "unknown")
        plan.setdefault("last_active_section", None)
        plan.setdefault("block_decisions", [])
        plan.setdefault("chunks", [])

        for key in ("document_title", "last_active_section"):
            if plan.get(key) == "":
                plan[key] = None

        for decision in plan["block_decisions"]:
            decision.setdefault("section_title", None)
            decision.setdefault("parent_section", None)
            decision.setdefault("section_level", None)
            decision.setdefault("include_in_retrieval", True)
            decision.setdefault("exclusion_reason", None)
            decision.setdefault("duplicate_group", None)
            decision.setdefault("duplicate_of", None)
            decision.setdefault("confidence", 1.0)
            for key in (
                "section_title",
                "parent_section",
                "exclusion_reason",
                "duplicate_group",
                "duplicate_of",
            ):
                if decision.get(key) == "":
                    decision[key] = None
            if decision.get("section_level") == 0:
                decision["section_level"] = None

        for chunk in plan["chunks"]:
            chunk.setdefault("section_title", None)
            chunk.setdefault("parent_section", None)
            chunk.setdefault("topic", "")
            chunk.setdefault("summary", "")
            chunk.setdefault("confidence", 1.0)
            for key in ("section_title", "parent_section"):
                if chunk.get(key) == "":
                    chunk[key] = None

        return plan

    @staticmethod
    def _validate_plan(
        plan: ModelDocumentPlan,
        blocks: list[LayoutBlock],
    ) -> None:
        expected = {block.block_id for block in blocks}
        block_map = {block.block_id: block for block in blocks}
        decision_ids = [decision.block_id for decision in plan.block_decisions]

        if Counter(decision_ids) != Counter(expected):
            missing = sorted(expected - set(decision_ids))
            unknown = sorted(set(decision_ids) - expected)
            repeated = sorted(
                block_id
                for block_id, count in Counter(decision_ids).items()
                if count > 1
            )
            raise ModelChunkingError(
                "Model block coverage is invalid. "
                f"missing={missing}, unknown={unknown}, repeated={repeated}"
            )

        chunk_ids = [
            block_id
            for chunk in plan.chunks
            for block_id in chunk.block_ids
        ]
        repeated_chunk_ids = sorted(
            block_id
            for block_id, count in Counter(chunk_ids).items()
            if count > 1
        )
        if repeated_chunk_ids:
            raise ModelChunkingError(
                "Blocks were assigned to multiple chunks: "
                f"{repeated_chunk_ids}"
            )

        unknown_chunk_ids = sorted(set(chunk_ids) - expected)
        if unknown_chunk_ids:
            raise ModelChunkingError(
                f"Chunks contain unknown block IDs: {unknown_chunk_ids}"
            )

        indexes = sorted(chunk.chunk_index for chunk in plan.chunks)
        if indexes != list(range(len(indexes))):
            raise ModelChunkingError(
                "Chunk indexes must be zero-based and contiguous: "
                f"{indexes}"
            )


    def _materialize(
        self,
        plan: ModelDocumentPlan,
        blocks: list[LayoutBlock],
        processed_ids: set[str],
        duplicate_groups: set[str],
        start_index: int,
    ) -> list[FinalChunk]:
        block_map = {block.block_id: block for block in blocks}
        decisions = {decision.block_id: decision for decision in plan.block_decisions}
        output: list[FinalChunk] = []

        for chunk in sorted(plan.chunks, key=lambda item: item.chunk_index):
            selected: list[LayoutBlock] = []
            for block_id in chunk.block_ids:
                if block_id in processed_ids:
                    continue
                processed_ids.add(block_id)
                decision = decisions[block_id]
                if not self._include(decision) or decision.duplicate_of:
                    continue
                if decision.duplicate_group in duplicate_groups:
                    continue
                if decision.duplicate_group:
                    duplicate_groups.add(decision.duplicate_group)
                selected.append(block_map[block_id])

            if not selected:
                continue

            selected.sort(key=lambda block: block.reading_order)
            try:
                local_groups = ChunkSizePostProcessor(
                    settings.MODEL_CHUNK_MAX_TOKENS
                ).split(selected)
            except ValueError as error:
                raise ModelChunkingError(str(error)) from error

            for local_group in local_groups:
                content = "\n\n".join(
                    block.text.strip()
                    for block in local_group
                    if block.text.strip()
                )
                if not content:
                    continue

                token_count = TokenCounter.estimate(content)
                output.append(
                    FinalChunk(
                        chunk_index=start_index + len(output),
                        content=content,
                        token_count=token_count,
                        page_start=min(block.page_number for block in local_group),
                        page_end=max(block.page_number for block in local_group),
                        block_ids=[block.block_id for block in local_group],
                        block_indexes=[block.block_index for block in local_group],
                        section_title=chunk.section_title,
                        parent_section=chunk.parent_section,
                        content_type=chunk.content_type,
                        topic=chunk.topic,
                        summary=chunk.summary,
                        confidence=chunk.confidence,
                        chunking_method="model_hierarchical_v3",
                        chunking_provider=settings.DOCUMENT_CHUNKING_PROVIDER,
                        chunking_model=self.model,
                        planner_window=self.planner_window,
                        planner_concurrency=self.planner_concurrency,
                    )
                )

        return output

    def _propagate_missing_sections(
        self,
        chunks: list[FinalChunk],
    ) -> list[FinalChunk]:
        result = list(chunks)
        for index, chunk in enumerate(result):
            if chunk.section_title or chunk.content_type == "document_title":
                continue
            previous = next(
                (
                    item.section_title
                    for item in reversed(result[:index])
                    if item.section_title
                ),
                None,
            )
            following = next(
                (
                    item.section_title
                    for item in result[index + 1 :]
                    if item.section_title
                ),
                None,
            )
            inherited = previous if previous == following else previous or following
            if inherited:
                result[index] = chunk.model_copy(
                    update={"section_title": inherited}
                )
        return result

    def _merge_tiny_chunks(
        self,
        chunks: list[FinalChunk],
    ) -> list[FinalChunk]:
        if len(chunks) < 2:
            return chunks

        pending = list(chunks)
        result: list[FinalChunk] = []
        mergeable = {"document_title", "figure_caption", "table_caption"}
        index = 0

        while index < len(pending):
            chunk = pending[index]
            if chunk.token_count >= 50 or chunk.content_type not in mergeable:
                result.append(chunk)
                index += 1
                continue

            if result:
                previous = result[-1]
                combined = f"{previous.content}\n\n{chunk.content}".strip()
                if TokenCounter.estimate(combined) <= settings.MODEL_CHUNK_MAX_TOKENS:
                    result[-1] = self._combine_chunks(previous, chunk, combined)
                    index += 1
                    continue

            if index + 1 < len(pending):
                following = pending[index + 1]
                combined = f"{chunk.content}\n\n{following.content}".strip()
                if TokenCounter.estimate(combined) <= settings.MODEL_CHUNK_MAX_TOKENS:
                    pending[index + 1] = self._combine_chunks(
                        chunk,
                        following,
                        combined,
                        keep_semantics_from=following,
                    )
                    index += 1
                    continue

            result.append(chunk)
            index += 1

        return result

    @staticmethod
    def _combine_chunks(
        first: FinalChunk,
        second: FinalChunk,
        content: str,
        *,
        keep_semantics_from: FinalChunk | None = None,
    ) -> FinalChunk:
        semantic = keep_semantics_from or first
        return semantic.model_copy(
            update={
                "content": content,
                "token_count": TokenCounter.estimate(content),
                "page_start": min(first.page_start, second.page_start),
                "page_end": max(first.page_end, second.page_end),
                "block_ids": first.block_ids + second.block_ids,
                "block_indexes": first.block_indexes + second.block_indexes,
            }
        )

    @staticmethod
    def _reindex_chunks(chunks: list[FinalChunk]) -> list[FinalChunk]:
        return [
            chunk.model_copy(update={"chunk_index": index})
            for index, chunk in enumerate(chunks)
        ]

    @classmethod
    def _build_diagnostics(
        cls,
        *,
        blocks: list[LayoutBlock],
        decisions: dict[str, BlockDecision],
        chunks: list[FinalChunk],
    ) -> dict[str, Any]:
        expected_ids = {block.block_id for block in blocks}
        decision_ids = set(decisions)
        included_ids = {
            block_id
            for block_id, decision in decisions.items()
            if (
                cls._include(decision)
                and not decision.duplicate_of
            )
        }
        excluded = {
            block_id: {
                "block_type": decision.block_type,
                "reason": decision.exclusion_reason or "excluded_by_policy",
            }
            for block_id, decision in decisions.items()
            if not cls._include(decision)
        }
        chunk_ids = {
            block_id
            for chunk in chunks
            for block_id in chunk.block_ids
        }

        # Overlapping planner batches can return different decisions for the
        # same block. Membership in a validated final chunk is authoritative.
        included_ids |= chunk_ids

        excluded = {
            block_id: details
            for block_id, details in excluded.items()
            if block_id not in chunk_ids
        }

        return {
            "refined_block_count": len(expected_ids),
            "decision_count": len(decision_ids),
            "decision_coverage_percent": round(
                100 * len(expected_ids & decision_ids) / max(1, len(expected_ids)),
                2,
            ),
            "missing_decision_ids": sorted(expected_ids - decision_ids),
            "included_block_count": len(included_ids),
            "excluded_block_count": len(excluded),
            "included_coverage_percent": round(
                100 * len(included_ids & chunk_ids) / max(1, len(included_ids)),
                2,
            ),
            "missing_included_ids": sorted(included_ids - chunk_ids),
            "unexpected_chunk_ids": sorted(chunk_ids - included_ids),
            "excluded_blocks": excluded,
            "block_decisions": {
                block_id: decision.model_dump()
                for block_id, decision in decisions.items()
            },
        }

    @staticmethod
    def _include(decision: BlockDecision) -> bool:
        if not decision.include_in_retrieval:
            return False
        if decision.block_type in {"header", "footer", "noise"}:
            return False
        if decision.block_type == "reference" and not settings.MODEL_CHUNK_INCLUDE_REFERENCES:
            return False
        if (
            decision.block_type in {"figure_caption", "table_caption"}
            and not settings.MODEL_CHUNK_INCLUDE_CAPTIONS
        ):
            return False
        if decision.block_type == "table" and not settings.MODEL_CHUNK_INCLUDE_TABLES:
            return False
        return True

    @staticmethod
    def _validate_final(chunks: list[FinalChunk]) -> None:
        if [chunk.chunk_index for chunk in chunks] != list(range(len(chunks))):
            raise ModelChunkingError("Final chunk indexes are invalid.")
        ids = [block_id for chunk in chunks for block_id in chunk.block_ids]
        if len(ids) != len(set(ids)):
            raise ModelChunkingError("Final chunks contain duplicate block membership.")
