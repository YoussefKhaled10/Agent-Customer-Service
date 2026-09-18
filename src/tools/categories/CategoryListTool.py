from __future__ import annotations

from typing import Any, Callable, ContextManager
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.models.Database import database_session
from src.models.db_schemes.agent_db.schemes.category import Category
from src.models.db_schemes.agent_db.schemes.product import Product
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface


class CategoryListTool(ToolInterface):
    def __init__(self, session_factory: Callable[[], ContextManager[Session]] = database_session) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="category_list",
            description="List active catalog categories with active in-stock product counts.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "in_stock_only": {"type": "boolean"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("categories", "catalog", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        in_stock_only = bool(arguments.get("in_stock_only", True))
        limit = int(arguments.get("limit", 50))
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")
        with self.session_factory() as session:
            product_filters = [Product.category_id == Category.id, Product.is_active.is_(True)]
            if in_stock_only:
                product_filters.append((Product.stock - Product.reserved_stock) > 0)
            product_count = select(func.count(Product.id)).where(*product_filters).correlate(Category).scalar_subquery()
            statement = select(Category, product_count.label("available_products")).where(Category.is_active.is_(True))
            if query:
                pattern = f"%{query}%"
                statement = statement.where(Category.name.ilike(pattern) | Category.slug.ilike(pattern))
            rows = session.execute(statement.order_by(Category.name).limit(limit)).all()
        categories = [
            {
                "category_id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "available_products": int(count or 0),
                "is_active": category.is_active,
            }
            for category, count in rows
        ]
        return {"count": len(categories), "categories": categories, "filters": {"query": query or None, "in_stock_only": in_stock_only, "limit": limit}}
