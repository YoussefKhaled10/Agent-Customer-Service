from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import InquiryPriority, InquiryStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer


class CustomerInquiry(TimestampMixin, Base):
    __tablename__ = "customer_inquiries"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    subject: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[InquiryPriority] = mapped_column(
        Enum(
            InquiryPriority,
            name="inquiry_priority",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=InquiryPriority.NORMAL,
        nullable=False,
        index=True,
    )
    status: Mapped[InquiryStatus] = mapped_column(
        Enum(
            InquiryStatus,
            name="inquiry_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=InquiryStatus.OPEN,
        nullable=False,
        index=True,
    )

    customer: Mapped["Customer | None"] = relationship(back_populates="inquiries")
