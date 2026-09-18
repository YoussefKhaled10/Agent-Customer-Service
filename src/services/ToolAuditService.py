from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ToolExecutionModel import ToolExecutionModel


class ToolAuditService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def record(
        self,
        *,
        conversation_id: int,
        message_id: int | None,
        result: dict[str, Any],
        input_json: dict[str, Any],
    ) -> None:
        with self.session_factory() as session:
            record, started_at = ToolExecutionModel.start(
                session,
                tool_name=result.get("tool_name", "unknown"),
                input_json=input_json,
                conversation_id=conversation_id,
                message_id=message_id,
                request_id=result.get("request_id"),
            )
            if result.get("success"):
                ToolExecutionModel.succeed(
                    session,
                    record,
                    started_at,
                    output_json={
                        "data": result.get("data"),
                        "message": result.get("message"),
                    },
                )
            else:
                ToolExecutionModel.fail(
                    session,
                    record,
                    started_at,
                    result.get("message")
                    or result.get("error_code")
                    or "Tool execution failed",
                )
