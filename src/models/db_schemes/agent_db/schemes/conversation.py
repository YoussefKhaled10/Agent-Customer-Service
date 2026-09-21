from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import ConversationStatus, MessageRole

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer
    from src.models.db_schemes.agent_db.schemes.tool_execution import ToolExecution


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id = Column(
        String(150), unique=True, nullable=False, index=True
    )
    status = Column(
        Enum(
            ConversationStatus,
            name="conversation_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    language = Column(String(20), nullable=True)
    pending_action = Column(JSONB, nullable=True)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", 
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )
    tool_executions = relationship("ToolExecution", 
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(
        Enum(
            MessageRole,
            name="message_role",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True, index=True)
    sub_intent = Column(String(100), nullable=True)
    safety_level = Column(String(50), nullable=True, index=True)
    message_metadata = Column(JSONB, default=dict, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation = relationship("Conversation", back_populates="messages")
    tool_executions = relationship("ToolExecution", 
        back_populates="message"
    )
