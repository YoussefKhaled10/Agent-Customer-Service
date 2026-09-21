from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Column, Integer, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.category import Category
    from src.models.db_schemes.agent_db.schemes.order import OrderItem


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("stock >= 0", name="stock_non_negative"),
        CheckConstraint("reserved_stock >= 0", name="reserved_stock_non_negative"),
        CheckConstraint("reserved_stock <= stock", name="reserved_stock_not_greater_than_stock"),
    )

    id = Column(Integer, primary_key=True)
    category_id = Column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(220), unique=True, nullable=False, index=True)
    sku = Column(String(80), unique=True, nullable=False, index=True)
    brand = Column(String(120), nullable=True, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EGP", nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    reserved_stock = Column(Integer, default=0, nullable=False)
    short_description = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    features_json = Column(JSONB, default=dict, nullable=False)
    warnings_json = Column(JSONB, default=list, nullable=False)
    image_url = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    @property
    def available_stock(self) -> int:
        return self.stock - self.reserved_stock

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku!r}>"
