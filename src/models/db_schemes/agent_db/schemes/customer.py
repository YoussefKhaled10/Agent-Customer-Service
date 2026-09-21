from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import CustomerRole

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.conversation import Conversation
    from src.models.db_schemes.agent_db.schemes.customer_inquiry import CustomerInquiry
    from src.models.db_schemes.agent_db.schemes.order import Order
    from src.models.db_schemes.agent_db.schemes.pharmacist_request import PharmacistRequest


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True, index=True)
    default_shipping_address = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    role = Column(

        String(32),

        nullable=False,

        default=CustomerRole.CUSTOMER.value,

        server_default=CustomerRole.CUSTOMER.value,

        index=True,

    )

    orders = relationship("Order", back_populates="customer", lazy="selectin")
    inquiries = relationship("CustomerInquiry", back_populates="customer")
    pharmacist_requests = relationship("PharmacistRequest", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"
