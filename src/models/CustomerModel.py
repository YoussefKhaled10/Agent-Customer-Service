from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.db_schemes.agent_db.schemes.customer import Customer


class CustomerModel:
    """Database operations for the customers table."""

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        if phone is None:
            return None

        normalized_phone = phone.strip()
        return normalized_phone or None

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if limit < 1 or limit > 500:
            raise ValueError("Limit must be between 1 and 500.")
        if offset < 0:
            raise ValueError("Offset cannot be negative.")

    @classmethod
    def get_by_id(
        cls,
        session: Session,
        customer_id: int,
    ) -> Customer | None:
        if customer_id < 1:
            return None
        return session.get(Customer, customer_id)

    @classmethod
    def get_by_email(
        cls,
        session: Session,
        email: str,
    ) -> Customer | None:
        normalized_email = cls.normalize_email(email)
        if not normalized_email:
            return None

        statement = select(Customer).where(
            func.lower(Customer.email) == normalized_email
        )
        return session.scalar(statement)

    @classmethod
    def create(
        cls,
        session: Session,
        name: str,
        email: str,
        hashed_password: str | None = None,
        phone: str | None = None,
        default_shipping_address: str | None = None,
    ) -> Customer:
        normalized_name = name.strip()
        normalized_email = cls.normalize_email(email)
        normalized_phone = cls.normalize_phone(phone)
        normalized_address = (
            default_shipping_address.strip()
            if default_shipping_address
            else None
        )

        if not normalized_name:
            raise ValueError("Customer name is required.")
        if not normalized_email:
            raise ValueError("Customer email is required.")
        if cls.get_by_email(session, normalized_email) is not None:
            raise ValueError("A customer with this email already exists.")

        customer = Customer(
            name=normalized_name,
            email=normalized_email,
            hashed_password=hashed_password,
            phone=normalized_phone,
            default_shipping_address=normalized_address or None,
            is_active=True,
        )
        session.add(customer)

        try:
            session.flush()
        except IntegrityError as error:
            session.rollback()
            raise ValueError(
                "The customer could not be created because the email already exists."
            ) from error

        return customer

    @classmethod
    def get_or_create(
        cls,
        session: Session,
        name: str,
        email: str,
        phone: str | None = None,
        default_shipping_address: str | None = None,
    ) -> tuple[Customer, bool]:
        customer = cls.get_by_email(session, email)
        if customer is not None:
            return customer, False

        customer = cls.create(
            session=session,
            name=name,
            email=email,
            phone=phone,
            default_shipping_address=default_shipping_address,
        )
        return customer, True

    @classmethod
    def update(
        cls,
        session: Session,
        customer_id: int,
        name: str | None = None,
        phone: str | None = None,
        default_shipping_address: str | None = None,
    ) -> Customer:
        customer = cls.get_by_id(session, customer_id)
        if customer is None:
            raise ValueError("Customer was not found.")

        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("Customer name cannot be empty.")
            customer.name = normalized_name

        if phone is not None:
            customer.phone = cls.normalize_phone(phone)

        if default_shipping_address is not None:
            customer.default_shipping_address = (
                default_shipping_address.strip() or None
            )

        session.flush()
        return customer

    @classmethod
    def set_active_status(
        cls,
        session: Session,
        customer_id: int,
        is_active: bool,
    ) -> Customer:
        customer = cls.get_by_id(session, customer_id)
        if customer is None:
            raise ValueError("Customer was not found.")

        customer.is_active = is_active
        session.flush()
        return customer

    @classmethod
    def deactivate(cls, session: Session, customer_id: int) -> Customer:
        return cls.set_active_status(session, customer_id, False)

    @classmethod
    def activate(cls, session: Session, customer_id: int) -> Customer:
        return cls.set_active_status(session, customer_id, True)

    @classmethod
    def list_customers(
        cls,
        session: Session,
        active_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        cls._validate_pagination(limit, offset)

        statement: Select[tuple[Customer]] = select(Customer)

        if active_only:
            statement = statement.where(Customer.is_active.is_(True))

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                Customer.name.ilike(pattern)
                | Customer.email.ilike(pattern)
                | Customer.phone.ilike(pattern)
            )

        statement = (
            statement
            .order_by(Customer.created_at.desc(), Customer.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(statement).all())
