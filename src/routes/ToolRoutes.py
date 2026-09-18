from __future__ import annotations

from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify, request

from src.core.AuthenticationDependencies import optional_customer_id
from src.schemas.ToolSchemas import ToolExecutionRequest
from src.services.ToolBootstrapService import ToolBootstrapService
from src.services.ToolExecutionService import ToolExecutionService
from src.tools.ToolRegistry import ToolRegistry


def create_tools_blueprint(
    registry: ToolRegistry | None = None,
    executor: ToolExecutionService | None = None,
) -> Blueprint:
    active_registry = registry or ToolBootstrapService.create_registry()
    active_executor = executor or ToolExecutionService(active_registry)
    blueprint = Blueprint("tools", __name__, url_prefix="/api/tools")

    @blueprint.get("")
    def list_tools():
        return jsonify(
            {
                "count": len(active_registry),
                "tools": active_registry.model_schemas(),
            }
        ), 200

    @blueprint.post("/execute")
    def execute_tool():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "Request body must be a JSON object.",
                }
            ), 422

        allowed_fields = {"tool_name", "arguments", "request_id", "confirmed", "metadata"}
        unexpected = sorted(set(payload) - allowed_fields)
        if unexpected:
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "Unexpected request fields: " + ", ".join(unexpected),
                }
            ), 422

        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "tool_name must be a non-empty string.",
                }
            ), 422
        if not isinstance(arguments, dict):
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "arguments must be a JSON object.",
                }
            ), 422

        customer_id, auth_error = optional_customer_id()
        if auth_error is not None:
            return auth_error

        execution_request = ToolExecutionRequest(
            tool_name=tool_name.strip(),
            arguments=arguments,
            request_id=_optional_string(payload.get("request_id")),
            user_id=customer_id,
            confirmed=bool(payload.get("confirmed", False)),
            metadata=payload.get("metadata", {})
            if isinstance(payload.get("metadata", {}), dict)
            else {},
        )
        result = active_executor.execute(execution_request)
        status_code = _status_code(result.error_code)
        return jsonify(asdict(result)), status_code

    return blueprint


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _status_code(error_code: str | None) -> int:
    if error_code is None:
        return 200
    return {
        "authentication_required": 401,
        "tool_not_found": 404,
        "invalid_tool_arguments": 422,
        "confirmation_required": 409,
    }.get(error_code, 500)
