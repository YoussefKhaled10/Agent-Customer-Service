from __future__ import annotations

import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


_GMAIL_LOCAL_PATTERN = re.compile(r"^[A-Za-z0-9.]+$")
_EGYPTIAN_MOBILE_PATTERN = re.compile(r"^01[0125][0-9]{8}$")
_UPPERCASE_PATTERN = re.compile(r"[A-Z]")
_LOWERCASE_PATTERN = re.compile(r"[a-z]")
_DIGIT_PATTERN = re.compile(r"[0-9]")
_SYMBOL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    phone: str | None = Field(default=None, max_length=30)
    default_shipping_address: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("email")
    @classmethod
    def validate_gmail_address(cls, value: EmailStr) -> EmailStr:
        normalized = str(value).strip().lower()
        local_part, separator, domain = normalized.rpartition("@")

        errors: list[str] = []
        if not separator or domain != "gmail.com":
            errors.append("Email address must use the gmail.com domain.")

        if (
            not local_part
            or not _GMAIL_LOCAL_PATTERN.fullmatch(local_part)
            or local_part.startswith(".")
            or local_part.endswith(".")
            or ".." in local_part
        ):
            errors.append(
                "Gmail username may contain only letters, numbers, and single dots, "
                "and dots cannot be at the beginning or end."
            )

        if errors:
            raise ValueError(" ".join(errors))

        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        missing: list[str] = []

        if not _UPPERCASE_PATTERN.search(value):
            missing.append("at least one uppercase letter")
        if not _LOWERCASE_PATTERN.search(value):
            missing.append("at least one lowercase letter")
        if not _DIGIT_PATTERN.search(value):
            missing.append("at least one number")
        if not _SYMBOL_PATTERN.search(value):
            missing.append("at least one special symbol")

        if missing:
            raise ValueError(
                "Password is missing: " + ", ".join(missing) + "."
            )

        return value

    @field_validator("phone")
    @classmethod
    def validate_and_normalize_egyptian_phone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        compact = re.sub(r"[\s()-]", "", value)
        if compact.startswith("+20"):
            compact = "0" + compact[3:]
        elif compact.startswith("0020"):
            compact = "0" + compact[4:]

        if not _EGYPTIAN_MOBILE_PATTERN.fullmatch(compact):
            raise ValueError(
                "Phone number must be a valid Egyptian mobile number with 11 digits "
                "starting with 010, 011, 012, or 015."
            )

        return compact


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: EmailStr) -> EmailStr:
        return str(value).strip().lower()


class CustomerResponse(BaseModel):
    customer_id: int
    name: str
    email: EmailStr
    phone: str | None
    default_shipping_address: str | None
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: CustomerResponse
