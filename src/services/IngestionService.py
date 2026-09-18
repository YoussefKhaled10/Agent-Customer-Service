from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from src.exceptions.IngestionExceptions import IngestionError
from src.ingestion.model_ingestion_pipeline import ModelIngestionPipeline
from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import IndexStatus, KnowledgeCategory
from src.schemas.IngestionSchemas import IngestionResult
from src.stores.llm import LLMFactory, LLMInterface
from src.stores.vectordb import VectorDBFactory, VectorDBInterface


class IngestionService:
    def __init__(
        self,
        embedding_provider: LLMInterface | None = None,
        vector_store: VectorDBInterface | None = None,
        pipeline: ModelIngestionPipeline | None = None,
    ) -> None:
        self.pipeline = pipeline or ModelIngestionPipeline()
        self.embedding_provider = embedding_provider or LLMFactory.create()
        self.vector_store = vector_store or VectorDBFactory.create()

    def ingest_pdf(
        self,
        file_path: str | Path,
        title: str,
        category: KnowledgeCategory,
        tags: list[str] | None = None,
        force: bool = False,
    ) -> IngestionResult:
        path = Path(file_path).expanduser().resolve()
        file_hash = self._file_hash(path)

        raw_blocks = self.pipeline.extractor.extract(path)
        refined_blocks = self.pipeline.refiner.refine(raw_blocks)
        chunks = self.pipeline.chunker.chunk(refined_blocks)

        if not raw_blocks:
            raise IngestionError("The PDF extractor did not produce source blocks.")
        if not refined_blocks:
            raise IngestionError("The layout refiner did not produce model input blocks.")
        if not chunks:
            raise IngestionError("The document model did not produce retrieval chunks.")

        pages_processed = max(block.page_number for block in raw_blocks)
        full_text = "\n\n".join(
            block.text
            for block in raw_blocks
            if block.text.strip()
        )

        with database_session() as session:
            existing = self.vector_store.find_active_document_by_hash(
                session,
                file_hash,
            )

            if existing is not None and not force:
                return IngestionResult(
                    document_id=existing.id,
                    title=existing.title,
                    file_name=path.name,
                    file_hash=file_hash,
                    pages_processed=pages_processed,
                    blocks_extracted=len(refined_blocks),
                    chunks_created=len(existing.chunks),
                    embedding_dimension=(
                        existing.embedding_dimension
                        or self.embedding_provider.dimension
                    ),
                    index_status=existing.index_status.value,
                    duplicate=True,
                )

            if existing is not None:
                document = existing
                document.title = title
                document.content = full_text
                document.category = category
                document.tags = tags or []
                document.content_hash = file_hash
                document.index_status = IndexStatus.PENDING
                document.index_error = None
            else:
                document = self.vector_store.create_document(
                    session,
                    title=title,
                    content=full_text,
                    category=category,
                    tags=tags or [],
                )
                document.content_hash = file_hash

            session.flush()
            document_id = document.id
            document_title = document.title

        try:
            vectors = self.embedding_provider.embed_documents(
                [chunk.content for chunk in chunks]
            )

            if len(vectors) != len(chunks):
                raise IngestionError(
                    "Embedding count does not match the number of generated chunks."
                )

            payload = [
                self._chunk_payload(
                    file_name=path.name,
                    file_hash=file_hash,
                    chunk=chunk,
                    vector=vector,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]

            with database_session() as session:
                self.vector_store.replace_chunks(
                    session,
                    document_id,
                    payload,
                    self.embedding_provider.model,
                    self.embedding_provider.dimension,
                )

            return IngestionResult(
                document_id=document_id,
                title=document_title,
                file_name=path.name,
                file_hash=file_hash,
                pages_processed=pages_processed,
                blocks_extracted=len(refined_blocks),
                chunks_created=len(payload),
                embedding_dimension=self.embedding_provider.dimension,
                index_status=IndexStatus.INDEXED.value,
                duplicate=False,
            )

        except Exception as error:
            with database_session() as session:
                self.vector_store.mark_failed(
                    session,
                    document_id,
                    str(error),
                )

            if isinstance(error, IngestionError):
                raise

            raise IngestionError(
                f"PDF ingestion failed: {error}"
            ) from error

    def replace_document(
        self,
        document_id: int,
        file_path: str | Path,
    ) -> IngestionResult:
        from src.models.KnowledgeModel import KnowledgeModel
        from src.models.db_schemes.agent_db.schemes.knowledge import KnowledgeDocument
        
        path = Path(file_path).expanduser().resolve()
        file_hash = self._file_hash(path)

        raw_blocks = self.pipeline.extractor.extract(path)
        refined_blocks = self.pipeline.refiner.refine(raw_blocks)
        chunks = self.pipeline.chunker.chunk(refined_blocks)

        if not raw_blocks:
            raise IngestionError("The PDF extractor did not produce source blocks.")
        if not refined_blocks:
            raise IngestionError("The layout refiner did not produce model input blocks.")
        if not chunks:
            raise IngestionError("The document model did not produce retrieval chunks.")

        pages_processed = max(block.page_number for block in raw_blocks)
        full_text = "\n\n".join(
            block.text
            for block in raw_blocks
            if block.text.strip()
        )

        vectors = self.embedding_provider.embed_documents(
            [chunk.content for chunk in chunks]
        )

        if len(vectors) != len(chunks):
            raise IngestionError(
                "Embedding count does not match the number of generated chunks."
            )

        payload = [
            self._chunk_payload(
                file_name=path.name,
                file_hash=file_hash,
                chunk=chunk,
                vector=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

        with database_session() as session:
            document = session.get(KnowledgeDocument, document_id)
            if document is None:
                raise IngestionError("Document not found.")
            
            document.content = full_text
            document.content_hash = file_hash
            document_title = document.title
            
            self.vector_store.replace_chunks(
                session,
                document_id,
                payload,
                self.embedding_provider.model,
                self.embedding_provider.dimension,
            )

        return IngestionResult(
            document_id=document_id,
            title=document_title,
            file_name=path.name,
            file_hash=file_hash,
            pages_processed=pages_processed,
            blocks_extracted=len(refined_blocks),
            chunks_created=len(payload),
            embedding_dimension=self.embedding_provider.dimension,
            index_status=IndexStatus.INDEXED.value,
            duplicate=False,
        )

    def _chunk_payload(
        self,
        file_name: str,
        file_hash: str,
        chunk: Any,
        vector: list[float],
    ) -> dict[str, Any]:
        metadata = {
            "source_type": "pdf",
            "file_name": file_name,
            "file_hash": file_hash,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "block_ids": chunk.block_ids,
            "block_indexes": chunk.block_indexes,
            "section_title": chunk.section_title,
            "parent_section": chunk.parent_section,
            "content_type": chunk.content_type,
            "topic": chunk.topic,
            "summary": chunk.summary,
            "confidence": chunk.confidence,
            "chunking_method": chunk.chunking_method,
            "document_model": self.pipeline.chunker.model,
            "embedding_model": self.embedding_provider.model,
        }

        return {
            "content": chunk.content,
            "token_count": chunk.token_count,
            "metadata": metadata,
            "embedding": vector,
        }

    @staticmethod
    def _file_hash(path: Path) -> str:
        if not path.is_file():
            raise IngestionError(
                f"PDF file not found: {path}"
            )

        digest = sha256()

        with path.open("rb") as file_handle:
            for part in iter(
                lambda: file_handle.read(1024 * 1024),
                b"",
            ):
                digest.update(part)

        return digest.hexdigest()
