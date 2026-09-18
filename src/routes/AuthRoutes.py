from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from src.core.AuthenticationDependencies import require_customer
from src.core.JWTService import JWTService
from src.exceptions.AuthenticationExceptions import AuthenticationError
from src.schemas.AuthenticationSchemas import LoginRequest, RegisterRequest
from src.services.AuthenticationService import AuthenticationService


def create_auth_blueprint(
    auth_service: AuthenticationService | None = None,
    jwt_service: JWTService | None = None,
) -> Blueprint:
    service = auth_service or AuthenticationService()
    token_service = jwt_service or service.jwt_service
    blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")

    @blueprint.post("/register")
    def register():
        return _execute(lambda: service.register(RegisterRequest.model_validate(request.get_json(silent=True) or {})), 201)

    @blueprint.post("/login")
    def login():
        return _execute(lambda: service.login(LoginRequest.model_validate(request.get_json(silent=True) or {})), 200)

    @blueprint.get("/me")
    @require_customer(token_service)
    def me():
        return _execute(lambda: service.get_customer(g.current_customer_id), 200)

    return blueprint


def _execute(operation, success_status: int):
    try:
        result = operation()
        return jsonify(result.model_dump(mode="json")), success_status
    except ValidationError as error:
        return jsonify({"error": "validation_error", "message": "Request data is invalid.", "details": error.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )}), 422
    except AuthenticationError as error:
        return jsonify({"error": error.error_code, "message": str(error)}), error.status_code
    except ValueError as error:
        return jsonify({"error": "invalid_request", "message": str(error)}), 400
