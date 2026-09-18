from __future__ import annotations

from flask import Blueprint, jsonify, request

from src.core.AuthenticationDependencies import optional_customer_id
from src.services.ChatHistoryService import ChatHistoryService


def create_conversation_blueprint(
    history_service: ChatHistoryService | None = None,
) -> Blueprint:
    blueprint = Blueprint(
        "chat_history",
        __name__,
        url_prefix="/api/chat/conversations",
    )
    service = history_service or ChatHistoryService()

    def authenticated_customer():
        customer_id, auth_error = optional_customer_id()
        if auth_error is not None:
            return None, auth_error
        if customer_id is None:
            return None, (
                jsonify(
                    {
                        "error": "authentication_required",
                        "message": "Sign in to access saved conversations.",
                    }
                ),
                401,
            )
        return customer_id, None

    @blueprint.get("")
    def list_conversations():
        customer_id, auth_error = authenticated_customer()
        if auth_error is not None:
            return auth_error
        limit = request.args.get("limit", 30, type=int)
        return jsonify(
            {
                "conversations": service.list_for_customer(
                    customer_id,
                    limit=limit,
                )
            }
        )

    @blueprint.get("/<string:session_id>/messages")
    def conversation_messages(session_id: str):
        customer_id, auth_error = authenticated_customer()
        if auth_error is not None:
            return auth_error
        result = service.messages_for_customer(customer_id, session_id)
        if result is None:
            return jsonify(
                {
                    "error": "conversation_not_found",
                    "message": "Conversation was not found.",
                }
            ), 404
        return jsonify(result)

    return blueprint
