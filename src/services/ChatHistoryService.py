from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, ContextManager

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import MessageRole
from src.models.db_schemes.agent_db.schemes.conversation import Conversation


class ChatHistoryService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def list_for_customer(
        self,
        customer_id: int,
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        limit = min(max(int(limit), 1), 100)
        with self.session_factory() as session:
            conversations = list(
                session.scalars(
                    select(Conversation)
                    .options(selectinload(Conversation.messages))
                    .where(Conversation.customer_id == customer_id)
                    .order_by(
                        Conversation.updated_at.desc(),
                        Conversation.id.desc(),
                    )
                    .limit(limit)
                ).all()
            )

            return [self._conversation_summary(item) for item in conversations]

    def messages_for_customer(
        self,
        customer_id: int,
        session_id: str,
    ) -> dict[str, Any] | None:
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            return None

        with self.session_factory() as session:
            conversation = session.scalar(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    Conversation.customer_id == customer_id,
                    Conversation.session_id == normalized_session_id,
                )
            )
            if conversation is None:
                return None

            return {
                "conversation": self._conversation_summary(conversation),
                "messages": [
                    {
                        "id": message.id,
                        "role": self._enum_value(message.role),
                        "content": message.content,
                        "created_at": self._iso(message.created_at),
                    }
                    for message in conversation.messages
                ],
            }

    @classmethod
    def _conversation_summary(cls, conversation: Conversation) -> dict[str, Any]:
        user_messages = [
            message.content
            for message in conversation.messages
            if cls._enum_value(message.role) == MessageRole.USER.value
        ]
        first_message = user_messages[0] if user_messages else "New conversation"
        title = cls._title(first_message)
        last_message = (
            conversation.messages[-1].content
            if conversation.messages
            else ""
        )
        last_activity = (
            conversation.messages[-1].created_at
            if conversation.messages
            else conversation.updated_at
        )
        return {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "title": title,
            "preview": cls._preview(last_message),
            "message_count": len(conversation.messages),
            "status": cls._enum_value(conversation.status),
            "has_pending_action": conversation.pending_action is not None,
            "updated_at": cls._iso(last_activity),
        }

    @staticmethod
    def _title(value: str, limit: int = 42) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized or "New conversation"
        return normalized[: limit - 1].rstrip() + "…"

    @staticmethod
    def _preview(value: str, limit: int = 72) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
