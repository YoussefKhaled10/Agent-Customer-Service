from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.db_schemes.agent_db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.db_schemes.agent_db.schemes.product import Product


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    products = relationship("Product", 
        back_populates="category",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
