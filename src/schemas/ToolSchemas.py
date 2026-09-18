from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    requires_authentication: bool = False
    requires_confirmation: bool = False
    is_idempotent: bool = True
    tags: tuple[str, ...] = ()

    def to_model_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    user_id: int | None = None
    request_id: str | None = None
    confirmed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    user_id: int | None = None
    confirmed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def execution_context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            user_id=self.user_id,
            request_id=self.request_id,
            confirmed=self.confirmed,
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    success: bool
    tool_name: str
    data: Any = None
    message: str | None = None
    error_code: str | None = None
    execution_time_ms: float = 0.0
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
