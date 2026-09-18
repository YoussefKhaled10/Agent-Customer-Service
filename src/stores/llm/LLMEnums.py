from enum import StrEnum


class LLMProvider(StrEnum):
    COHERE = "cohere"
    GEMINI = "gemini"
    GROQ = "groq"


class EmbeddingInputType(StrEnum):
    DOCUMENT = "search_document"
    QUERY = "search_query"
