from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import InquiryPriority, InquiryStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer


class CustomerInquiry(TimestampMixin, Base):
    __tablename__ = "customer_inquiries"

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name = Column(String(150), nullable=False)
    email = Column(String(320), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    subject = Column(String(250), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(
        Enum(
            InquiryPriority,
            name="inquiry_priority",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=InquiryPriority.NORMAL,
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(
            InquiryStatus,
            name="inquiry_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=InquiryStatus.OPEN,
        nullable=False,
        index=True,
    )

    customer = relationship("Customer", back_populates="inquiries")
