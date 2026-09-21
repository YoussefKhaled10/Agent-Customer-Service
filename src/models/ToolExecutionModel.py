from time import perf_counter
from typing import Any
from sqlalchemy.orm import Session
from src.models.db_schemes.agent_db.enums import ToolExecutionStatus
from src.models.db_schemes.agent_db.schemes.tool_execution import ToolExecution

class ToolExecutionModel:
    @classmethod
    def start(cls, session: Session, tool_name: str, input_json: dict[str, Any],
              conversation_id: int | None = None, message_id: int | None = None,
              request_id: str | None = None) -> tuple[ToolExecution, float]:
        record = ToolExecution(conversation_id=conversation_id, message_id=message_id,
            tool_name=tool_name, input_json=input_json, status=ToolExecutionStatus.PENDING,
            request_id=request_id)
        session.add(record)
        session.flush()
        return record, perf_counter()

    @classmethod
    def succeed(cls, session: Session, record: ToolExecution, started_at: float,
                output_json: dict[str, Any]) -> ToolExecution:
        record.status = ToolExecutionStatus.SUCCESS
        record.output_json = output_json
        record.execution_time_ms = int((perf_counter() - started_at) * 1000)
        session.flush()
        return record

    @classmethod
    def fail(cls, session: Session, record: ToolExecution, started_at: float,
             error: Exception | str) -> ToolExecution:
        record.status = ToolExecutionStatus.FAILED
        record.error_message = str(error)[:2000]
        record.execution_time_ms = int((perf_counter() - started_at) * 1000)
        session.flush()
        return record
