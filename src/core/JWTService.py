from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from src.exceptions.AuthenticationExceptions import InvalidTokenError
from src.helpers.config import settings


class JWTService:
    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        expire_minutes: int | None = None,
    ) -> None:
        self.secret_key = secret_key or settings.JWT_SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.expire_minutes = (
            expire_minutes
            if expire_minutes is not None
            else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        if len(self.secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters.")
        if self.expire_minutes < 1:
            raise ValueError("JWT access token lifetime must be positive.")

    def create_access_token(self, customer_id: int) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.expire_minutes)
        payload = {
            "sub": str(customer_id),
            "type": "access",
            "iat": now,
            "exp": expires_at,
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, self.expire_minutes * 60

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "exp", "iat", "type"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise InvalidTokenError("Access token has expired.") from error
        except jwt.PyJWTError as error:
            raise InvalidTokenError("Access token is invalid.") from error

        if payload.get("type") != "access":
            raise InvalidTokenError("Token type is invalid.")
        try:
            customer_id = int(payload["sub"])
        except (TypeError, ValueError) as error:
            raise InvalidTokenError("Token subject is invalid.") from error
        if customer_id < 1:
            raise InvalidTokenError("Token subject is invalid.")
        payload["customer_id"] = customer_id
        return payload
