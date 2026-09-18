from __future__ import annotations

from typing import Callable, ContextManager

from sqlalchemy.orm import Session

from src.core.JWTService import JWTService
from src.core.PasswordHasher import PasswordHasher
from src.exceptions.AuthenticationExceptions import (
    CustomerNotFoundError,
    EmailAlreadyRegisteredError,
    InactiveCustomerError,
    InvalidCredentialsError,
)
from src.models.CustomerModel import CustomerModel
from src.models.Database import database_session
from src.schemas.AuthenticationSchemas import (
    CustomerResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)


class AuthenticationService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
        password_hasher: PasswordHasher | None = None,
        jwt_service: JWTService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.password_hasher = password_hasher or PasswordHasher()
        self.jwt_service = jwt_service or JWTService()

    def register(self, payload: RegisterRequest) -> TokenResponse:
        with self.session_factory() as session:
            if CustomerModel.get_by_email(session, str(payload.email)) is not None:
                raise EmailAlreadyRegisteredError("A customer with this email already exists.")
            customer = CustomerModel.create(
                session=session,
                name=payload.name,
                email=str(payload.email),
                hashed_password=self.password_hasher.hash(payload.password),
                phone=payload.phone,
                default_shipping_address=payload.default_shipping_address,
            )
            customer_data = self._customer_response(customer)
        token, expires_in = self.jwt_service.create_access_token(customer_data.customer_id)
        return TokenResponse(access_token=token, expires_in=expires_in, customer=customer_data)

    def login(self, payload: LoginRequest) -> TokenResponse:
        with self.session_factory() as session:
            customer = CustomerModel.get_by_email(session, str(payload.email))
            if customer is None or not self.password_hasher.verify(payload.password, customer.hashed_password):
                raise InvalidCredentialsError("Email or password is incorrect.")
            if not customer.is_active:
                raise InactiveCustomerError("Customer account is inactive.")
            customer_data = self._customer_response(customer)
        token, expires_in = self.jwt_service.create_access_token(customer_data.customer_id)
        return TokenResponse(access_token=token, expires_in=expires_in, customer=customer_data)

    def get_customer(self, customer_id: int) -> CustomerResponse:
        with self.session_factory() as session:
            customer = CustomerModel.get_by_id(session, customer_id)
            if customer is None:
                raise CustomerNotFoundError("Customer was not found.")
            if not customer.is_active:
                raise InactiveCustomerError("Customer account is inactive.")
            return self._customer_response(customer)

    @staticmethod
    def _customer_response(customer) -> CustomerResponse:
        return CustomerResponse(
            customer_id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            default_shipping_address=customer.default_shipping_address,
            is_active=customer.is_active,
        )
