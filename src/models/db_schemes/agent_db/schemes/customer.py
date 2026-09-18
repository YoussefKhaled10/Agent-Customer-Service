from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import CustomerRole

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.conversation import Conversation
    from src.models.db_schemes.agent_db.schemes.customer_inquiry import CustomerInquiry
    from src.models.db_schemes.agent_db.schemes.order import Order
    from src.models.db_schemes.agent_db.schemes.pharmacist_request import PharmacistRequest


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    default_shipping_address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)

    role: Mapped[str] = mapped_column(

        String(32),

        nullable=False,

        default=CustomerRole.CUSTOMER.value,

        server_default=CustomerRole.CUSTOMER.value,

        index=True,

    )

    orders: Mapped[list["Order"]] = relationship(back_populates="customer", lazy="selectin")
    inquiries: Mapped[list["CustomerInquiry"]] = relationship(back_populates="customer")
    pharmacist_requests: Mapped[list["PharmacistRequest"]] = relationship(back_populates="customer")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"
