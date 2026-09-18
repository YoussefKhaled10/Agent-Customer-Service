from __future__ import annotations


class HybridRetrievalService:
    """Hybrid retrieval boundary. Fusion is enabled after keyword retrieval."""

    def retrieve(self, query: str, limit: int = 8):
        raise NotImplementedError("Hybrid retrieval is not enabled yet.")
