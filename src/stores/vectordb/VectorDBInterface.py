from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class VectorDBInterface(ABC):
    @abstractmethod
    def find_active_document_by_hash(self, session: Session, file_hash: str):
        """Return an active document with the supplied content hash."""

    @abstractmethod
    def create_document(self, session: Session, **data):
        """Create a knowledge document."""

    @abstractmethod
    def replace_chunks(
        self,
        session: Session,
        document_id: int,
        chunks: list[dict[str, Any]],
        embedding_model: str,
        embedding_dimension: int,
    ):
        """Replace all chunks and vectors belonging to a document."""

    @abstractmethod
    def mark_failed(self, session: Session, document_id: int, error: str):
        """Mark document indexing as failed."""
