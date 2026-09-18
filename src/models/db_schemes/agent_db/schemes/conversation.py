from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import ConversationStatus, MessageRole

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer
    from src.models.db_schemes.agent_db.schemes.tool_execution import ToolExecution


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(
            ConversationStatus,
            name="conversation_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pending_action: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    customer: Mapped["Customer | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(
            MessageRole,
            name="message_role",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sub_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="message"
    )
