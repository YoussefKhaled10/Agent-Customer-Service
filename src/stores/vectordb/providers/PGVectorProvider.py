from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models.KnowledgeModel import KnowledgeModel
from src.models.db_schemes.agent_db.schemes.knowledge import KnowledgeDocument
from src.stores.vectordb.VectorDBInterface import VectorDBInterface


class PGVectorProvider(VectorDBInterface):
    def find_active_document_by_hash(self, session: Session, file_hash: str):
        return session.scalar(
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .where(
                KnowledgeDocument.content_hash == file_hash,
                KnowledgeDocument.is_active.is_(True),
            )
        )

    def create_document(self, session: Session, **data):
        return KnowledgeModel.create_document(session=session, **data)

    def replace_chunks(
        self,
        session: Session,
        document_id: int,
        chunks: list[dict[str, Any]],
        embedding_model: str,
        embedding_dimension: int,
    ):
        return KnowledgeModel.replace_chunks(
            session, document_id, chunks, embedding_model, embedding_dimension
        )

    def mark_failed(self, session: Session, document_id: int, error: str):
        return KnowledgeModel.mark_failed(session, document_id, error)
