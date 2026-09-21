from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import ContactMethod, PharmacistRequestStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer
    from src.models.db_schemes.agent_db.schemes.product import Product


class PharmacistRequest(TimestampMixin, Base):
    __tablename__ = "pharmacist_requests"

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    related_product_id = Column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name = Column(String(150), nullable=False)
    email = Column(String(320), nullable=True, index=True)
    phone = Column(String(30), nullable=False, index=True)
    preferred_contact_method = Column(
        Enum(
            ContactMethod,
            name="contact_method",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ContactMethod.PHONE,
        nullable=False,
    )
    question_summary = Column(Text, nullable=False)
    status = Column(
        Enum(
            PharmacistRequestStatus,
            name="pharmacist_request_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=PharmacistRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to = Column(String(150), nullable=True)
    internal_notes = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="pharmacist_requests")
    related_product = relationship("Product", )
