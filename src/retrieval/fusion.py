from __future__ import annotations

from dataclasses import replace

from src.schemas.RetrievalSchemas import SearchHit


class ReciprocalRankFusion:
    def __init__(self, rank_constant: int = 60) -> None:
        if rank_constant < 1:
            raise ValueError("rank_constant must be positive.")
        self.rank_constant = rank_constant

    def fuse(
        self,
        semantic_hits: list[SearchHit],
        keyword_hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if limit < 1:
            raise ValueError("Fusion limit must be positive.")

        merged: dict[int, SearchHit] = {}
        scores: dict[int, float] = {}
        semantic_ranks: dict[int, int] = {}
        keyword_ranks: dict[int, int] = {}

        for rank, hit in enumerate(semantic_hits, start=1):
            merged[hit.chunk_id] = hit
            semantic_ranks[hit.chunk_id] = rank
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (
                self.rank_constant + rank
            )

        for rank, hit in enumerate(keyword_hits, start=1):
            existing = merged.get(hit.chunk_id)
            merged[hit.chunk_id] = (
                replace(existing, keyword_score=hit.keyword_score)
                if existing is not None
                else hit
            )
            keyword_ranks[hit.chunk_id] = rank
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (
                self.rank_constant + rank
            )

        ordered_ids = sorted(
            merged,
            key=lambda chunk_id: (-scores[chunk_id], chunk_id),
        )
        return [
            replace(
                merged[chunk_id],
                hybrid_score=scores[chunk_id],
                semantic_rank=semantic_ranks.get(chunk_id),
                keyword_rank=keyword_ranks.get(chunk_id),
            )
            for chunk_id in ordered_ids[:limit]
        ]
