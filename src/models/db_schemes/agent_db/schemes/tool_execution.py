from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base
from src.models.db_schemes.agent_db.enums import ToolExecutionStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.conversation import Conversation, Message


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    message_id = Column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tool_name = Column(String(150), nullable=False, index=True)
    input_json = Column(JSONB, default=dict, nullable=False)
    output_json = Column(JSONB, nullable=True)
    status = Column(
        Enum(
            ToolExecutionStatus,
            name="tool_execution_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ToolExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    request_id = Column(String(150), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation = relationship("Conversation", 
        back_populates="tool_executions"
    )
    message = relationship("Message", back_populates="tool_executions")
