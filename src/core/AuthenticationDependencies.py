from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import g, jsonify, request

from src.core.JWTService import JWTService
from src.exceptions.AuthenticationExceptions import InvalidTokenError

F = TypeVar("F", bound=Callable[..., Any])


def _bearer_token() -> str | None:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token.strip():
        return None
    return token.strip()


def optional_customer_id(
    jwt_service: JWTService | None = None,
) -> tuple[int | None, tuple[Any, int] | None]:
    """Return an authenticated customer id when a Bearer token is present.

    Missing tokens are allowed because public tools may execute anonymously.
    Invalid or expired tokens are rejected instead of silently becoming anonymous.
    """
    token = _bearer_token()
    if token is None:
        return None, None

    service = jwt_service or JWTService()
    try:
        payload = service.decode_access_token(token)
    except InvalidTokenError as error:
        return None, (
            jsonify({"error": error.error_code, "message": str(error)}),
            401,
        )

    return int(payload["customer_id"]), None


def require_customer(
    jwt_service: JWTService | None = None,
) -> Callable[[F], F]:
    service = jwt_service or JWTService()

    def decorator(function: F) -> F:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any):
            token = _bearer_token()
            if token is None:
                return jsonify(
                    {
                        "error": "authentication_required",
                        "message": "Bearer access token is required.",
                    }
                ), 401

            try:
                payload = service.decode_access_token(token)
            except InvalidTokenError as error:
                return jsonify(
                    {"error": error.error_code, "message": str(error)}
                ), 401

            g.current_customer_id = int(payload["customer_id"])
            return function(*args, **kwargs)

        return cast(F, wrapped)

    return decorator
