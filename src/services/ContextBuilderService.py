from __future__ import annotations

from src.schemas.ContextSchemas import BuiltContext, ContextItem
from src.schemas.RetrievalSchemas import RetrievalHit


class ContextBuilderService:
    """Build a compact, cited context from already reranked retrieval hits."""

    def build(
        self,
        hits: list[RetrievalHit],
        *,
        token_budget: int = 2400,
        max_chunks: int = 5,
        minimum_score: float | None = None,
    ) -> BuiltContext:
        if token_budget < 1:
            raise ValueError("token_budget must be positive.")
        if max_chunks < 1:
            raise ValueError("max_chunks must be positive.")

        selected: list[ContextItem] = []
        seen_chunk_ids: set[int] = set()
        total_tokens = 0
        skipped_duplicates = 0
        skipped_budget = 0
        skipped_score = 0

        for hit in hits:
            if len(selected) >= max_chunks:
                break

            if hit.chunk_id in seen_chunk_ids:
                skipped_duplicates += 1
                continue
            seen_chunk_ids.add(hit.chunk_id)

            score = self._relevance_score(hit)
            if minimum_score is not None and (
                score is None or score < minimum_score
            ):
                skipped_score += 1
                continue

            token_count = max(1, int(hit.token_count or 0))
            if total_tokens + token_count > token_budget:
                skipped_budget += 1
                continue

            metadata = hit.metadata or {}
            item = ContextItem(
                source_id=f"S{len(selected) + 1}",
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                chunk_index=hit.chunk_index,
                content=hit.content.strip(),
                token_count=token_count,
                page_start=self._optional_int(metadata.get("page_start")),
                page_end=self._optional_int(metadata.get("page_end")),
                document_title=self._optional_text(
                    metadata.get("document_title") or metadata.get("title")
                ),
                file_name=self._optional_text(metadata.get("file_name")),
                section_title=self._optional_text(metadata.get("section_title")),
                topic=self._optional_text(metadata.get("topic")),
                content_type=self._optional_text(metadata.get("content_type")),
                relevance_score=score,
                metadata=dict(metadata),
            )
            selected.append(item)
            total_tokens += token_count

        return BuiltContext(
            text=self._render(selected),
            items=selected,
            total_tokens=total_tokens,
            token_budget=token_budget,
            candidate_count=len(hits),
            selected_count=len(selected),
            skipped_duplicate_count=skipped_duplicates,
            skipped_budget_count=skipped_budget,
            skipped_score_count=skipped_score,
        )

    @staticmethod
    def _relevance_score(hit: RetrievalHit) -> float | None:
        for value in (
            hit.rerank_score,
            hit.hybrid_score,
            hit.semantic_score,
            hit.keyword_score,
        ):
            if value is not None:
                return float(value)
        return None

    @staticmethod
    def _optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _render(items: list[ContextItem]) -> str:
        blocks: list[str] = []
        for item in items:
            header_parts = [
                f"[{item.source_id}]",
                f"document_id={item.document_id}",
                f"chunk_index={item.chunk_index}",
            ]
            if item.document_title:
                header_parts.append(f"title={item.document_title}")
            elif item.file_name:
                header_parts.append(f"file={item.file_name}")
            if item.page_start is not None:
                pages = str(item.page_start)
                if item.page_end is not None and item.page_end != item.page_start:
                    pages = f"{item.page_start}-{item.page_end}"
                header_parts.append(f"pages={pages}")
            if item.section_title:
                header_parts.append(f"section={item.section_title}")
            if item.topic:
                header_parts.append(f"topic={item.topic}")

            blocks.append(" | ".join(header_parts) + "\n" + item.content)

        return "\n\n".join(blocks)
