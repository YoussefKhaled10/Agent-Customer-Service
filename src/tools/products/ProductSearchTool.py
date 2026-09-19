from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ProductModel import ProductModel
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface
from src.tools.products.ProductToolHelpers import serialize_product


class ProductSearchTool(ToolInterface):
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="product_search",
            description=(
                "Search active PharmaCare products by name, brand, SKU, description, "
                "category, price range, and stock availability."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "query_variants": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "maxItems": 6,
                        "uniqueItems": True,
                        "description": (
                            "Arabic and English equivalents, corrected spellings, or concise "
                            "catalog keywords for the same user intent."
                        ),
                    },
                    "category_id": {"type": "integer", "minimum": 1},
                    "category_slug": {"type": "string", "minLength": 1},
                    "category_name": {"type": "string", "minLength": 1},
                    "min_price": {"type": "number", "minimum": 0},
                    "max_price": {"type": "number", "minimum": 0},
                    "in_stock_only": {"type": "boolean"},
                    "limit": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("products", "search", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        raw_queries = [arguments.get("query"), *(arguments.get("query_variants") or [])]
        normalized_queries = list(dict.fromkeys(
            " ".join(str(value).split())
            for value in raw_queries
            if value is not None and str(value).strip()
        ))
        combined_query = " ".join(normalized_queries) or None
        search_terms = ProductModel.search_terms(combined_query)
        min_price = self._decimal_or_none(arguments.get("min_price"), "min_price")
        max_price = self._decimal_or_none(arguments.get("max_price"), "max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price.")

        with self.session_factory() as session:
            products = ProductModel.search(
                session=session,
                query=combined_query,
                category_id=arguments.get("category_id"),
                category_slug=arguments.get("category_slug"),
                category_name=arguments.get("category_name"),
                min_price=min_price,
                max_price=max_price,
                in_stock_only=arguments.get("in_stock_only", True),
                limit=arguments.get("limit", 20),
            )
            serialized = [serialize_product(product) for product in products]

        return {
            "count": len(serialized),
            "products": serialized,
            "filters": {
                "query": arguments.get("query"),
                "query_variants": normalized_queries,
                "search_terms": search_terms,
                "match_mode": "any_term_any_field" if search_terms else None,
                "category_id": arguments.get("category_id"),
                "category_slug": arguments.get("category_slug"),
                "category_name": arguments.get("category_name"),
                "min_price": None if min_price is None else format(min_price, ".2f"),
                "max_price": None if max_price is None else format(max_price, ".2f"),
                "in_stock_only": arguments.get("in_stock_only", True),
                "limit": arguments.get("limit", 20),
            },
        }

    @staticmethod
    def _decimal_or_none(value: Any, field_name: str) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"{field_name} must be a valid non-negative number.") from error
