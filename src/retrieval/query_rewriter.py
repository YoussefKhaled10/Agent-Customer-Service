from __future__ import annotations

from typing import Any

from src.helpers.config import settings
from src.schemas.RetrievalSchemas import RewrittenQuery
from src.stores.llm.AnswerProviderFactory import AnswerProviderFactory
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class QueryRewriteError(Exception):
    pass


class QueryRewriter:
    SYSTEM_PROMPT = """
You rewrite questions for retrieval only. Do not answer.
Detect language, correct obvious spelling errors, normalize colloquial wording,
and preserve intent, negation, names, drug names, numbers, dates, and technical
qualifiers. Return a semantic_query in the user's language and a keyword_query
in English for English documents. Return JSON only with detected_language,
normalized_query, semantic_query, keyword_query, keywords, and was_rewritten.
""".strip()

    RESPONSE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {
            "detected_language": {"type": "string"},
            "normalized_query": {"type": "string"},
            "semantic_query": {"type": "string"},
            "keyword_query": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "was_rewritten": {"type": "boolean"},
        },
        "required": ["detected_language", "normalized_query", "semantic_query", "keyword_query", "keywords", "was_rewritten"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        provider: AnswerProviderInterface | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or settings.RETRIEVAL_QUERY_REWRITE_MODEL
        self.provider = provider or AnswerProviderFactory.create(
            settings.QUERY_REWRITE_PROVIDER,
            model=self.model,
        )

    def rewrite(self, query: str) -> RewrittenQuery:
        original = query.strip()
        if not original:
            raise QueryRewriteError("The retrieval query cannot be empty.")
        try:
            payload = self.provider.generate_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=f"Rewrite for retrieval. Return JSON only.\n{original}",
                json_schema=self.RESPONSE_SCHEMA,
            )
            return self._validate_payload(original, payload)
        except QueryRewriteError:
            raise
        except Exception as error:
            raise QueryRewriteError(f"Query rewriting failed: {error}") from error

    @staticmethod
    def _validate_payload(original: str, payload: Any) -> RewrittenQuery:
        if not isinstance(payload, dict):
            raise QueryRewriteError("Query rewrite response must be a JSON object.")
        payload = dict(payload)
        payload["original_query"] = original
        return RewrittenQuery(**payload)
