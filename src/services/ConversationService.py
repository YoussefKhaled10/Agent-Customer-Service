from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.ConversationModel import ConversationModel
from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import MessageRole


class ConversationService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def load_or_create(
        self,
        *,
        session_id: str,
        customer_id: int | None,
        language: str | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            conversation, _ = ConversationModel.get_or_create(
                session,
                session_id,
                customer_id=customer_id,
                language=language,
            )
            if (
                customer_id is not None
                and conversation.customer_id is None
            ):
                conversation.customer_id = customer_id
                session.flush()
            history = [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in conversation.messages[-12:]
            ]
            return {
                "conversation_id": conversation.id,
                "history": history,
                "pending_action": conversation.pending_action,
            }

    def add_user_message(
        self,
        conversation_id: int,
        content: str,
    ) -> int:
        with self.session_factory() as session:
            message = ConversationModel.add_message(
                session,
                conversation_id,
                MessageRole.USER,
                content,
            )
            return message.id

    def add_assistant_message(
        self,
        conversation_id: int,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        with self.session_factory() as session:
            message = ConversationModel.add_message(
                session,
                conversation_id,
                MessageRole.ASSISTANT,
                content,
                metadata=metadata,
            )
            return message.id

    def set_pending_action(
        self,
        conversation_id: int,
        pending_action: dict[str, Any] | None,
    ) -> None:
        with self.session_factory() as session:
            ConversationModel.set_pending_action(
                session,
                conversation_id,
                pending_action,
            )
