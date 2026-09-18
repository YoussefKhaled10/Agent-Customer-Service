class IngestionError(Exception):
    """Base exception for ingestion failures."""


class InvalidPDFError(IngestionError):
    """Raised when a provided PDF is invalid or unsupported."""


class PDFSizeLimitError(IngestionError):
    """Raised when a PDF exceeds the configured file-size limit."""


class PDFPageLimitError(IngestionError):
    """Raised when a PDF exceeds the configured page limit."""


class PDFTextNotFoundError(IngestionError):
    """Raised when a PDF has insufficient extractable text."""


class ModelChunkingError(IngestionError):
    """Raised when model-driven document chunking fails."""


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
