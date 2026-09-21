from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Integer, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import IndexStatus, KnowledgeCategory


# Must match the embedding model selected before the first production migration.
EMBEDDING_DIMENSION = 384


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False, index=True)
    category = Column(
        Enum(
            KnowledgeCategory,
            name="knowledge_category",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=KnowledgeCategory.GENERAL,
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    tags = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    index_status = Column(
        Enum(
            IndexStatus,
            name="knowledge_index_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=IndexStatus.PENDING,
        nullable=False,
        index=True,
    )
    index_error = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    embedding_model = Column(String(200), nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    last_indexed_at = Column(
        DateTime(timezone=True), nullable=True
    )

    chunks = relationship("KnowledgeChunk", 
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="document_chunk_index_unique"),
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    chunk_identifier = Column(
        String(150), unique=True, nullable=False, index=True
    )
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    chunk_metadata = Column(JSONB, default=dict, nullable=False)
    embedding = Column(
        Vector(EMBEDDING_DIMENSION), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("KnowledgeDocument", back_populates="chunks")
