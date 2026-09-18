from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from src.models.Database import database_session
from src.models.db_schemes.agent_db.schemes.customer_inquiry import CustomerInquiry
from src.models.db_schemes.agent_db.schemes.pharmacist_request import PharmacistRequest
from src.models.db_schemes.agent_db.schemes.conversation import Conversation
from src.models.db_schemes.agent_db.schemes.tool_execution import ToolExecution

SENSITIVE = {"password","hashed_password","token","access_token","refresh_token","authorization","api_key","secret","database_url"}

def serialize_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE else serialize_safe(v)) for k,v in value.items()}
    if isinstance(value, list): return [serialize_safe(v) for v in value]
    return value

def enum_value(value: Any) -> str:
    return getattr(value, "value", value) or ""

@dataclass(slots=True)
class Page:
    items: list[Any]; total: int; page: int; pages: int

class AdminInquiryService:
    def list(self, query="", status="all", priority="all", page=1, per_page=20):
        q=query.strip(); filters=[]
        if q:
            p=f"%{q}%"; filters.append(or_(CustomerInquiry.subject.ilike(p),CustomerInquiry.customer_name.ilike(p),CustomerInquiry.email.ilike(p),CustomerInquiry.content.ilike(p)))
        if status!="all": filters.append(CustomerInquiry.status==status)
        if priority!="all": filters.append(CustomerInquiry.priority==priority)
        with database_session() as s:
            stmt=select(CustomerInquiry).where(*filters); total=int(s.scalar(select(func.count()).select_from(CustomerInquiry).where(*filters)) or 0)
            items=list(s.scalars(stmt.order_by(CustomerInquiry.created_at.desc()).offset((page-1)*per_page).limit(per_page)).all())
            for x in items: s.expunge(x)
        return Page(items,total,page,max(1,(total+per_page-1)//per_page))
    def get(self, item_id):
        with database_session() as s:
            x=s.get(CustomerInquiry,item_id)
            if not x: raise ValueError("Inquiry not found.")
            s.expunge(x); return x
    def update(self,item_id,status,priority):
        allowed_s={"open","in_progress","resolved","closed"}; allowed_p={"low","normal","high","urgent"}
        if status not in allowed_s or priority not in allowed_p: raise ValueError("Invalid status or priority.")
        with database_session() as s:
            x=s.get(CustomerInquiry,item_id)
            if not x: raise ValueError("Inquiry not found.")
            x.status=status; x.priority=priority; s.flush()

class AdminPharmacistService:
    def list(self,query="",status="all",page=1,per_page=20):
        q=query.strip(); filters=[]
        if q:
            p=f"%{q}%"; filters.append(or_(PharmacistRequest.customer_name.ilike(p),PharmacistRequest.email.ilike(p),PharmacistRequest.phone.ilike(p),PharmacistRequest.question_summary.ilike(p)))
        if status!="all": filters.append(PharmacistRequest.status==status)
        with database_session() as s:
            total=int(s.scalar(select(func.count()).select_from(PharmacistRequest).where(*filters)) or 0)
            items=list(s.scalars(select(PharmacistRequest).where(*filters).order_by(PharmacistRequest.created_at.desc()).offset((page-1)*per_page).limit(per_page)).all())
            for x in items: s.expunge(x)
        return Page(items,total,page,max(1,(total+per_page-1)//per_page))
    def get(self,item_id):
        with database_session() as s:
            x=s.get(PharmacistRequest,item_id)
            if not x: raise ValueError("Pharmacist request not found.")
            s.expunge(x); return x
    def update(self,item_id,status,assigned_to,internal_notes):
        allowed={"pending","assigned","contacted","resolved","cancelled"}
        if status not in allowed: raise ValueError("Invalid request status.")
        with database_session() as s:
            x=s.get(PharmacistRequest,item_id)
            if not x: raise ValueError("Pharmacist request not found.")
            x.status=status; x.assigned_to=assigned_to.strip() or None; x.internal_notes=internal_notes.strip() or None; s.flush()

class AdminConversationService:
    def list(self,query="",status="all",page=1,per_page=20):
        q=query.strip(); filters=[]
        if q: filters.append(Conversation.session_id.ilike(f"%{q}%"))
        if status!="all": filters.append(Conversation.status==status)
        with database_session() as s:
            total=int(s.scalar(select(func.count()).select_from(Conversation).where(*filters)) or 0)
            items=list(s.scalars(select(Conversation).where(*filters).options(selectinload(Conversation.messages)).order_by(Conversation.updated_at.desc()).offset((page-1)*per_page).limit(per_page)).all())
            for x in items: s.expunge(x)
        return Page(items,total,page,max(1,(total+per_page-1)//per_page))
    def get(self,item_id):
        with database_session() as s:
            x=s.scalar(select(Conversation).where(Conversation.id==item_id).options(selectinload(Conversation.messages),selectinload(Conversation.tool_executions)))
            if not x: raise ValueError("Conversation not found.")
            s.expunge(x); return x
    def clear_pending(self,item_id):
        with database_session() as s:
            x=s.get(Conversation,item_id)
            if not x: raise ValueError("Conversation not found.")
            x.pending_action=None; s.flush()

class AdminToolExecutionService:
    def list(self,query="",status="all",page=1,per_page=20):
        q=query.strip(); filters=[]
        if q: filters.append(or_(ToolExecution.tool_name.ilike(f"%{q}%"),ToolExecution.request_id.ilike(f"%{q}%")))
        if status!="all": filters.append(ToolExecution.status==status)
        with database_session() as s:
            total=int(s.scalar(select(func.count()).select_from(ToolExecution).where(*filters)) or 0)
            items=list(s.scalars(select(ToolExecution).where(*filters).order_by(ToolExecution.created_at.desc()).offset((page-1)*per_page).limit(per_page)).all())
            for x in items: s.expunge(x)
        return Page(items,total,page,max(1,(total+per_page-1)//per_page))
    def get(self,item_id):
        with database_session() as s:
            x=s.get(ToolExecution,item_id)
            if not x: raise ValueError("Tool execution not found.")
            data={"id":x.id,"tool_name":x.tool_name,"status":enum_value(x.status),"request_id":x.request_id,"conversation_id":x.conversation_id,"message_id":x.message_id,"execution_time_ms":x.execution_time_ms,"created_at":x.created_at,"input_json":serialize_safe(x.input_json),"output_json":serialize_safe(x.output_json),"error_message":"A tool execution error occurred." if x.error_message else None}
            return data
