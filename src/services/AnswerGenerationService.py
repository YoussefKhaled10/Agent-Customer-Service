from __future__ import annotations

from typing import Any

from src.schemas.AnswerSchemas import AnswerSource, GeneratedAnswer
from src.schemas.ContextSchemas import BuiltContext, ContextItem
from src.stores.llm.AnswerProviderFactory import AnswerProviderFactory
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class AnswerGenerationError(Exception):
    """Raised when a grounded answer cannot be generated or validated."""


class AnswerGenerationService:
    """Generate a concise grounded answer through the configured provider."""

    RESPONSE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "language": {"type": "string"},
            "answerable": {"type": "boolean"},
            "cited_source_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "answer",
            "language",
            "answerable",
            "cited_source_ids",
        ],
        "additionalProperties": False,
    }

    SYSTEM_PROMPT = """
You are a grounded question-answering component.
Use only the supplied SOURCES. Do not use outside knowledge and do not invent
facts. Answer in the requested language. Every factual statement must include
one or more inline source markers such as [S1] or [S1][S2]. Use only source IDs
that appear in SOURCES.

If the sources do not contain enough information, set answerable to false and
say that the available documents do not contain sufficient information. Do not
give personal diagnosis or personalized medical advice. Preserve important
names, numbers, qualifications, and uncertainty from the source text.
""".strip()

    def __init__(
        self,
        provider: AnswerProviderInterface | None = None,
    ) -> None:
        self.provider = provider or AnswerProviderFactory.create()

    def generate(
        self,
        *,
        query: str,
        detected_language: str,
        context: BuiltContext,
    ) -> GeneratedAnswer:
        normalized_query = query.strip()
        if not normalized_query:
            raise AnswerGenerationError("Answer query cannot be empty.")

        if not context.items or not context.text.strip():
            return GeneratedAnswer(
                answer=self._no_context_message(detected_language),
                language=detected_language or "unknown",
                answerable=False,
            )

        user_prompt = (
            f"REQUESTED_LANGUAGE: {detected_language or 'same as the question'}\n"
            f"QUESTION:\n{normalized_query}\n\n"
            f"SOURCES:\n{context.text}"
        )

        try:
            payload = self.provider.generate_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_schema=self.RESPONSE_SCHEMA,
            )
        except Exception as error:
            raise AnswerGenerationError(
                f"Grounded answer generation failed: {error}"
            ) from error

        return self._validate_payload(payload, context, detected_language)

    @classmethod
    def _validate_payload(
        cls,
        payload: Any,
        context: BuiltContext,
        detected_language: str,
    ) -> GeneratedAnswer:
        if not isinstance(payload, dict):
            raise AnswerGenerationError("Answer response must be a JSON object.")

        answer = str(payload.get("answer", "")).strip()
        language = str(
            payload.get("language", detected_language or "unknown")
        ).strip()
        answerable = bool(payload.get("answerable", False))
        raw_ids = payload.get("cited_source_ids", [])

        if not answer:
            raise AnswerGenerationError("Answer response is missing answer text.")
        if not isinstance(raw_ids, list):
            raise AnswerGenerationError("cited_source_ids must be an array.")

        item_by_id = {item.source_id: item for item in context.items}
        cited_ids: list[str] = []
        for value in raw_ids:
            source_id = str(value).strip()
            if source_id and source_id not in cited_ids:
                cited_ids.append(source_id)

        if not answerable:
            cited_ids = []

        unknown = [
            source_id
            for source_id in cited_ids
            if source_id not in item_by_id
        ]
        if unknown:
            raise AnswerGenerationError(
                "Answer cited unknown sources: " + ", ".join(unknown)
            )
        if answerable and not cited_ids:
            raise AnswerGenerationError(
                "An answerable response must cite at least one source."
            )

        answer = cls._ensure_inline_citations(
            answer=answer,
            cited_source_ids=cited_ids,
            answerable=answerable,
        )
        sources = [
            cls._to_answer_source(item_by_id[source_id])
            for source_id in cited_ids
        ]
        return GeneratedAnswer(
            answer=answer,
            language=language or detected_language or "unknown",
            answerable=answerable,
            cited_source_ids=cited_ids,
            sources=sources,
        )

    @staticmethod
    def _ensure_inline_citations(
        *,
        answer: str,
        cited_source_ids: list[str],
        answerable: bool,
    ) -> str:
        if not answerable or not cited_source_ids:
            return answer

        missing_markers = [
            f"[{source_id}]"
            for source_id in cited_source_ids
            if f"[{source_id}]" not in answer
        ]
        if not missing_markers:
            return answer

        return f"{answer.rstrip()} {' '.join(missing_markers)}"

    @staticmethod
    def _to_answer_source(item: ContextItem) -> AnswerSource:
        return AnswerSource(
            source_id=item.source_id,
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            chunk_index=item.chunk_index,
            page_start=item.page_start,
            page_end=item.page_end,
            document_title=item.document_title,
            file_name=item.file_name,
            section_title=item.section_title,
            topic=item.topic,
        )

    @staticmethod
    def _no_context_message(language: str) -> str:
        return (
            "المستندات المتاحة لا تحتوي على معلومات كافية للإجابة عن هذا السؤال."
            if language.casefold().startswith("ar")
            else "The available documents do not contain enough information to answer this question."
        )
