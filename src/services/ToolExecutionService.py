from __future__ import annotations

import time
from typing import Any

from src.exceptions.ToolExceptions import (
    ToolAuthenticationRequiredError,
    ToolConfirmationRequiredError,
    ToolError,
    ToolExecutionError,
    ToolValidationError,
)
from src.schemas.ToolSchemas import ToolExecutionRequest, ToolExecutionResult
from src.tools.ToolRegistry import ToolRegistry


class ToolExecutionService:
    """Validate and execute registered tools through a single safe boundary."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        started = time.perf_counter()
        try:
            tool = self.registry.get(request.tool_name)
            definition = tool.definition

            if definition.requires_authentication and request.user_id is None:
                raise ToolAuthenticationRequiredError(
                    f"Tool '{definition.name}' requires authentication."
                )
            if definition.requires_confirmation and not request.confirmed:
                raise ToolConfirmationRequiredError(
                    f"Tool '{definition.name}' requires user confirmation."
                )

            arguments = self._validate_arguments(
                request.arguments,
                definition.input_schema,
            )
            data = tool.execute(
                **arguments,
                _tool_context=request.execution_context(),
            )
            return self._result(
                started=started,
                success=True,
                tool_name=definition.name,
                data=data,
                message="Tool executed successfully.",
                request=request,
            )
        except ToolError as error:
            return self._result(
                started=started,
                success=False,
                tool_name=request.tool_name,
                message=str(error),
                error_code=error.error_code,
                request=request,
            )
        except Exception as error:
            wrapped = ToolExecutionError(
                f"Tool '{request.tool_name}' failed: {error}"
            )
            return self._result(
                started=started,
                success=False,
                tool_name=request.tool_name,
                message=str(wrapped),
                error_code=wrapped.error_code,
                request=request,
            )

    @classmethod
    def _validate_arguments(
        cls,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ToolValidationError("Tool arguments must be an object.")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_allowed = schema.get("additionalProperties", True)
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ToolValidationError(
                "Missing required arguments: " + ", ".join(missing)
            )
        if not additional_allowed:
            unexpected = [name for name in arguments if name not in properties]
            if unexpected:
                raise ToolValidationError(
                    "Unexpected arguments: " + ", ".join(unexpected)
                )
        for name, value in arguments.items():
            field_schema = properties.get(name)
            if field_schema is not None:
                cls._validate_value(name, value, field_schema)
        return dict(arguments)

    @classmethod
    def _validate_value(
        cls,
        name: str,
        value: Any,
        schema: dict[str, Any],
    ) -> None:
        expected_type = schema.get("type")
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        python_type = type_map.get(expected_type)
        if python_type is not None:
            valid = isinstance(value, python_type)
            if expected_type in {"integer", "number"} and isinstance(value, bool):
                valid = False
            if not valid:
                raise ToolValidationError(
                    f"Argument '{name}' must be of type {expected_type}."
                )
        if isinstance(value, str):
            minimum_length = schema.get("minLength")
            if minimum_length is not None and len(value) < minimum_length:
                raise ToolValidationError(
                    f"Argument '{name}' must contain at least {minimum_length} characters."
                )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = schema.get("minimum")
            if minimum is not None and value < minimum:
                raise ToolValidationError(
                    f"Argument '{name}' must be at least {minimum}."
                )
        allowed_values = schema.get("enum")
        if allowed_values is not None and value not in allowed_values:
            raise ToolValidationError(
                f"Argument '{name}' must be one of: {allowed_values}."
            )
        if isinstance(value, list) and "items" in schema:
            for index, item in enumerate(value):
                cls._validate_value(f"{name}[{index}]", item, schema["items"])
        if isinstance(value, list):
            minimum_items = schema.get("minItems")
            if minimum_items is not None and len(value) < minimum_items:
                raise ToolValidationError(
                    f"Argument '{name}' must contain at least {minimum_items} items."
                )

        if isinstance(value, str):
            maximum_length = schema.get("maxLength")
            if maximum_length is not None and len(value) > maximum_length:
                raise ToolValidationError(
                    f"Argument '{name}' must contain at most {maximum_length} characters."
                )

        if isinstance(value, dict):
            cls._validate_arguments(value, schema)

    @staticmethod
    def _result(
        *,
        started: float,
        success: bool,
        tool_name: str,
        request: ToolExecutionRequest,
        data: Any = None,
        message: str | None = None,
        error_code: str | None = None,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            success=success,
            tool_name=tool_name,
            data=data,
            message=message,
            error_code=error_code,
            execution_time_ms=round((time.perf_counter() - started) * 1000, 3),
            request_id=request.request_id,
            metadata=dict(request.metadata),
        )
