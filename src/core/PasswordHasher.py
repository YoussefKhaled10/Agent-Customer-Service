from __future__ import annotations

from pwdlib import PasswordHash


class PasswordHasher:
    """Hash and verify customer passwords using Argon2."""

    def __init__(self, password_hash: PasswordHash | None = None) -> None:
        self.password_hash = password_hash or PasswordHash.recommended()

    def hash(self, password: str) -> str:
        normalized = password.strip()
        if len(normalized) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        return self.password_hash.hash(normalized)

    def verify(self, password: str, hashed_password: str | None) -> bool:
        if not password or not hashed_password:
            return False
        try:
            return self.password_hash.verify(password, hashed_password)
        except Exception:
            return False
