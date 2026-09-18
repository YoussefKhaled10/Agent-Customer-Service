from __future__ import annotations


class KeywordQueryBuilder:
    """Build lexical queries when keyword retrieval is enabled."""

    def build(self, rewrite) -> str:
        return rewrite.keyword_query.strip()
