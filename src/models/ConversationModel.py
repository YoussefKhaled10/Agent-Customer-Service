from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.models.db_schemes.agent_db.enums import ConversationStatus, MessageRole
from src.models.db_schemes.agent_db.schemes.conversation import Conversation, Message

class ConversationModel:
    @classmethod
    def get_by_session_id(cls, session: Session, session_id: str) -> Conversation | None:
        return session.scalar(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.session_id == session_id))

    @classmethod
    def get_or_create(cls, session: Session, session_id: str,
                      customer_id: int | None = None, language: str | None = None) -> tuple[Conversation, bool]:
        conversation = cls.get_by_session_id(session, session_id)
        if conversation: return conversation, False
        conversation = Conversation(session_id=session_id, customer_id=customer_id,
                                    language=language, status=ConversationStatus.ACTIVE)
        session.add(conversation); session.flush(); return conversation, True

    @classmethod
    def add_message(cls, session: Session, conversation_id: int, role: MessageRole,
                    content: str, intent: str | None = None, sub_intent: str | None = None,
                    safety_level: str | None = None,
                    metadata: dict[str, Any] | None = None) -> Message:
        if not content.strip(): raise ValueError("Message content is required.")
        message = Message(conversation_id=conversation_id, role=role, content=content.strip(),
            intent=intent, sub_intent=sub_intent, safety_level=safety_level,
            message_metadata=metadata or {})
        session.add(message); session.flush(); return message

    @classmethod
    def set_pending_action(cls, session: Session, conversation_id: int,
                           pending_action: dict[str, Any] | None) -> Conversation:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None: raise ValueError("Conversation was not found.")
        conversation.pending_action = pending_action; session.flush(); return conversation
