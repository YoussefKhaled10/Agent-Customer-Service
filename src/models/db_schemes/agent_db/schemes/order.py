from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin
from src.models.db_schemes.agent_db.enums import OrderStatus

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.customer import Customer
    from src.models.db_schemes.agent_db.schemes.product import Product


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
    )

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    currency = Column(String(3), default="EGP", nullable=False)
    status = Column(
        Enum(
            OrderStatus,
            name="order_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    shipping_address = Column(String(1000), nullable=False)
    customer_notes = Column(String(1000), nullable=True)
    idempotency_key = Column(
        String(150), unique=True, nullable=False, index=True
    )

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", 
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} order_number={self.order_number!r}>"


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
    )

    id = Column(Integer, primary_key=True)
    order_id = Column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = Column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    product_name_snapshot = Column(String(200), nullable=False)
    product_sku_snapshot = Column(String(80), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} product_id={self.product_id} quantity={self.quantity}>"
