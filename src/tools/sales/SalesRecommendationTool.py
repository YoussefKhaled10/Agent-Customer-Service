from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ProductModel import ProductModel
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface
from src.tools.products.ProductToolHelpers import serialize_product


class SalesRecommendationTool(ToolInterface):
    """Recommend real, active products without generating medical claims."""

    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="sales_recommendation",
            description=(
                "Recommend active, in-stock PharmaCare products that match a user's "
                "stated product need and optional budget. This tool only uses stored "
                "catalog data and must not be used for diagnosis or prescriptions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 300,
                    },
                    "category_id": {"type": "integer", "minimum": 1},
                    "min_price": {"type": "number", "minimum": 0},
                    "max_price": {"type": "number", "minimum": 0},
                    "limit": {"type": "integer", "minimum": 1},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("sales", "products", "recommendation", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        query = str(arguments["query"]).strip()
        min_price = self._decimal_or_none(arguments.get("min_price"), "min_price")
        max_price = self._decimal_or_none(arguments.get("max_price"), "max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price.")

        limit = min(int(arguments.get("limit", 5)), 10)
        with self.session_factory() as session:
            products = ProductModel.search(
                session=session,
                query=query,
                category_id=arguments.get("category_id"),
                min_price=min_price,
                max_price=max_price,
                in_stock_only=True,
                limit=limit,
            )
            recommendations = [
                {
                    **serialize_product(product, include_details=True),
                    "match_reason": self._match_reason(product, query),
                }
                for product in products
            ]

        count = len(recommendations)
        return {
            "count": count,
            "recommendations": recommendations,
            "query": query,
            "matched": count > 0,
            "empty_result": count == 0,
            "message": (
                "Matching in-stock catalog recommendations were found."
                if count > 0
                else "No matching in-stock catalog recommendations were found."
            ),
            "notice": (
                "Recommendations are based only on catalog matching, price, and "
                "current availability. They are not medical advice."
            ),
        }

    @staticmethod
    def _decimal_or_none(value: Any, field_name: str) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"{field_name} must be a valid non-negative number.") from error

    @staticmethod
    def _match_reason(product: Any, query: str) -> str:
        normalized = query.casefold()
        matched_fields: list[str] = []
        candidates = {
            "name": product.name,
            "brand": product.brand,
            "SKU": product.sku,
            "description": product.short_description or product.description,
        }
        for label, value in candidates.items():
            if value and normalized in str(value).casefold():
                matched_fields.append(label)
        if matched_fields:
            return "Matched catalog " + ", ".join(matched_fields) + "."
        return "Matched the requested catalog filters and is currently in stock."
