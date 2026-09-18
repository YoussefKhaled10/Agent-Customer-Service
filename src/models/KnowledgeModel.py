from hashlib import sha256
from typing import Any
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session, selectinload
from src.models.db_schemes.agent_db.enums import IndexStatus, KnowledgeCategory
from src.models.db_schemes.agent_db.schemes.knowledge import KnowledgeChunk, KnowledgeDocument

class KnowledgeModel:
    @staticmethod
    def content_hash(content: str) -> str:
        return sha256(content.strip().encode("utf-8")).hexdigest()

    @classmethod
    def get_document(cls, session: Session, document_id: int) -> KnowledgeDocument | None:
        return session.scalar(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks)).where(KnowledgeDocument.id == document_id))

    @classmethod
    def create_document(cls, session: Session, *, title: str, content: str,
                        category: KnowledgeCategory = KnowledgeCategory.GENERAL,
                        tags: list[str] | None = None) -> KnowledgeDocument:
        if not title.strip() or not content.strip(): raise ValueError("Title and content are required.")
        document = KnowledgeDocument(title=title.strip(), content=content.strip(), category=category,
            tags=tags or [], is_active=True, index_status=IndexStatus.PENDING,
            content_hash=cls.content_hash(content))
        session.add(document); session.flush(); return document

    @classmethod
    def replace_chunks(cls, session: Session, document_id: int, chunks: list[dict[str, Any]],
                       embedding_model: str, embedding_dimension: int) -> KnowledgeDocument:
        document = cls.get_document(session, document_id)
        if document is None: raise ValueError("Knowledge document was not found.")
        session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
        for index, chunk in enumerate(chunks):
            session.add(KnowledgeChunk(document_id=document_id, chunk_index=index,
                chunk_identifier=f"kb_{document_id}_chunk_{index}", content=chunk["content"],
                token_count=chunk.get("token_count"), chunk_metadata=chunk.get("metadata", {}),
                embedding=chunk["embedding"]))
        document.embedding_model = embedding_model
        document.embedding_dimension = embedding_dimension
        document.index_status = IndexStatus.INDEXED
        document.index_error = None
        document.last_indexed_at = func.now()
        session.flush(); return document

    @classmethod
    def mark_failed(cls, session: Session, document_id: int, error: str) -> KnowledgeDocument:
        document = cls.get_document(session, document_id)
        if document is None: raise ValueError("Knowledge document was not found.")
        document.index_status = IndexStatus.FAILED; document.index_error = error[:2000]
        session.flush(); return document

    @classmethod
    def deactivate(cls, session: Session, document_id: int) -> KnowledgeDocument:
        document = cls.get_document(session, document_id)
        if document is None: raise ValueError("Knowledge document was not found.")
        document.is_active = False
        session.flush(); return document
