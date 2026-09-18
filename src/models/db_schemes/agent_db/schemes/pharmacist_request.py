from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import ContactMethod, PharmacistRequestStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer
    from src.models.db_schemes.agent_db.schemes.product import Product


class PharmacistRequest(TimestampMixin, Base):
    __tablename__ = "pharmacist_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    related_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    preferred_contact_method: Mapped[ContactMethod] = mapped_column(
        Enum(
            ContactMethod,
            name="contact_method",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=ContactMethod.PHONE,
        nullable=False,
    )
    question_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PharmacistRequestStatus] = mapped_column(
        Enum(
            PharmacistRequestStatus,
            name="pharmacist_request_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=PharmacistRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(150), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer | None"] = relationship(back_populates="pharmacist_requests")
    related_product: Mapped["Product | None"] = relationship()
