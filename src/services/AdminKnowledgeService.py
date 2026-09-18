from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import selectinload

from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import IndexStatus, KnowledgeCategory
from src.models.db_schemes.agent_db.schemes.knowledge import KnowledgeChunk, KnowledgeDocument
from src.services.IngestionService import IngestionService


UPLOAD_DIR = Path("uploads/knowledge")
REGISTRY_PATH = UPLOAD_DIR / "file_registry.json"


@dataclass(slots=True)
class KnowledgePage:
    documents: list[KnowledgeDocument]
    chunk_counts: dict[int, int]
    total: int
    page: int
    pages: int


class AdminKnowledgeService:
    def __init__(self, ingestion_service: IngestionService | None = None) -> None:
        self.ingestion = ingestion_service or IngestionService()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def category_choices() -> list[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ").title()) for item in KnowledgeCategory]

    def list_documents(self, *, query: str = "", status: str = "all", active: str = "all", page: int = 1, per_page: int = 12) -> KnowledgePage:
        page=max(1,page); query=query.strip(); filters=[]
        if query:
            pattern=f"%{query}%"; filters.append(or_(KnowledgeDocument.title.ilike(pattern), KnowledgeDocument.content_hash.ilike(pattern)))
        valid_status={item.value for item in IndexStatus}
        if status in valid_status: filters.append(KnowledgeDocument.index_status == status)
        if active == "active": filters.append(KnowledgeDocument.is_active.is_(True))
        elif active == "inactive": filters.append(KnowledgeDocument.is_active.is_(False))
        with database_session() as session:
            total=int(session.scalar(select(func.count()).select_from(KnowledgeDocument).where(*filters)) or 0)
            docs=list(session.scalars(select(KnowledgeDocument).where(*filters).order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id.desc()).offset((page-1)*per_page).limit(per_page)).all())
            ids=[doc.id for doc in docs]
            counts={}
            if ids:
                counts=dict(session.execute(select(KnowledgeChunk.document_id,func.count(KnowledgeChunk.id)).where(KnowledgeChunk.document_id.in_(ids)).group_by(KnowledgeChunk.document_id)).all())
            for doc in docs: session.expunge(doc)
        return KnowledgePage(docs,counts,total,page,max(1,(total+per_page-1)//per_page))

    def get_document(self, document_id: int) -> KnowledgeDocument:
        with database_session() as session:
            doc=session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id==document_id).options(selectinload(KnowledgeDocument.chunks)))
            if doc is None: raise ValueError("Knowledge document not found.")
            session.expunge(doc); return doc

    def upload(self, *, file_storage: Any, title: str, category: str, tags: str) -> Any:
        if not file_storage or not file_storage.filename: raise ValueError("A PDF file is required.")
        original=Path(file_storage.filename).name
        if Path(original).suffix.lower() != ".pdf": raise ValueError("Only PDF files are allowed.")
        safe="".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in original)
        destination=UPLOAD_DIR / safe
        counter=1
        while destination.exists():
            destination=UPLOAD_DIR / f"{Path(safe).stem}_{counter}.pdf"; counter+=1
        file_storage.save(destination)
        if destination.stat().st_size == 0:
            destination.unlink(missing_ok=True); raise ValueError("The uploaded PDF is empty.")
        try: selected=KnowledgeCategory(category)
        except ValueError: selected=KnowledgeCategory.GENERAL
        parsed_tags=[item.strip() for item in tags.split(",") if item.strip()]
        try:
            result=self.ingestion.ingest_pdf(destination,title.strip() or destination.stem,selected,parsed_tags)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        self._set_file(result.document_id,destination)
        return result

    def edit_metadata(self, document_id: int, title: str, category: str, tags: str) -> None:
        with database_session() as session:
            doc = session.get(KnowledgeDocument, document_id)
            if doc is None:
                raise ValueError("Knowledge document not found.")
            if title.strip():
                doc.title = title.strip()
            try:
                doc.category = KnowledgeCategory(category)
            except ValueError:
                pass
            doc.tags = [item.strip() for item in tags.split(",") if item.strip()]
            session.flush()

    def replace_pdf(self, document_id: int, file_storage: Any) -> Any:
        if not file_storage or not file_storage.filename:
            raise ValueError("A PDF file is required.")
        original = Path(file_storage.filename).name
        if Path(original).suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are allowed.")
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in original)
        destination = UPLOAD_DIR / safe
        counter = 1
        while destination.exists():
            destination = UPLOAD_DIR / f"{Path(safe).stem}_{counter}.pdf"
            counter += 1
        file_storage.save(destination)
        if destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            raise ValueError("The uploaded PDF is empty.")

        try:
            result = self.ingestion.replace_document(document_id, destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        self._set_file(document_id, destination)
        return result

    def set_active(self, document_id: int) -> bool:
        with database_session() as session:
            doc=session.get(KnowledgeDocument,document_id)
            if doc is None: raise ValueError("Knowledge document not found.")
            doc.is_active=not doc.is_active; session.flush(); return doc.is_active

    def reindex(self, document_id: int) -> Any:
        doc=self.get_document(document_id); source=self._get_file(document_id)
        if source is None or not source.is_file(): raise ValueError("The original PDF is unavailable. Upload it again instead.")
        return self.ingestion.ingest_pdf(source,doc.title,doc.category,list(doc.tags or []),force=True)

    def delete_document(self, document_id: int) -> None:
        source=self._get_file(document_id)
        with database_session() as session:
            doc=session.get(KnowledgeDocument,document_id)
            if doc is None: raise ValueError("Knowledge document not found.")
            session.delete(doc); session.flush()
        if source: source.unlink(missing_ok=True)
        registry=self._registry(); registry.pop(str(document_id),None); self._write_registry(registry)

    def _registry(self) -> dict[str,str]:
        if not REGISTRY_PATH.exists(): return {}
        try: return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError): return {}
    def _write_registry(self,data:dict[str,str])->None:
        REGISTRY_PATH.write_text(json.dumps(data,indent=2),encoding="utf-8")
    def _set_file(self,document_id:int,path:Path)->None:
        data=self._registry(); data[str(document_id)]=str(path.resolve()); self._write_registry(data)
    def _get_file(self,document_id:int)->Path|None:
        value=self._registry().get(str(document_id)); return Path(value) if value else None
