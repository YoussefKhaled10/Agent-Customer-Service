from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from src.core.AuthenticationDependencies import optional_customer_id
from src.schemas.AgentSchemas import AgentChatRequest
from src.services.AgentBootstrapService import AgentBootstrapService
from src.services.AgentService import AgentService

logger = logging.getLogger(__name__)


def create_agent_blueprint(
    agent_service: AgentService | None = None,
) -> Blueprint:
    blueprint = Blueprint(
        "agent",
        __name__,
        url_prefix="/api/agent",
    )
    active_service = (
        agent_service
        or AgentBootstrapService.create_agent_service()
    )

    @blueprint.post("/chat")
    def chat():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "Request body must be a JSON object.",
                    "details": [],
                }
            ), 422

        try:
            chat_request = AgentChatRequest.model_validate(payload)
        except ValidationError as error:
            return jsonify(
                {
                    "error": "validation_error",
                    "message": "Request data is invalid.",
                    "details": error.errors(
                        include_url=False,
                        include_context=False,
                        include_input=False,
                    ),
                }
            ), 422

        customer_id, auth_error = optional_customer_id()
        if auth_error is not None:
            return auth_error

        try:
            result = active_service.chat(
                message=chat_request.message,
                session_id=chat_request.session_id,
                customer_id=customer_id,
            )
        except Exception:
            logger.exception(
                "Agent execution failed for session_id=%s",
                chat_request.session_id,
            )
            return jsonify(
                {
                    "error": "agent_execution_error",
                    "message": (
                        "A temporary problem occurred while "
                        "processing the message."
                    ),
                }
            ), 500

        return jsonify(result.model_dump(mode="json")), 200

    return blueprint
