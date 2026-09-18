from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ProductModel import ProductModel
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface
from src.tools.products.ProductToolHelpers import serialize_product


class ProductDetailsTool(ToolInterface):
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="product_details",
            description=(
                "Get complete details for one active PharmaCare product using either "
                "product_id or SKU. Provide exactly one identifier."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "minimum": 1},
                    "sku": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("products", "details", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        product_id = arguments.get("product_id")
        sku = str(arguments.get("sku", "")).strip() or None
        if (product_id is None) == (sku is None):
            raise ValueError("Provide exactly one of product_id or sku.")

        with self.session_factory() as session:
            product = (
                ProductModel.get_by_id(session, product_id)
                if product_id is not None
                else ProductModel.get_by_sku(session, sku)
            )
            if product is None or not product.is_active:
                return {"found": False, "product": None}
            data = serialize_product(product, include_details=True)

        return {"found": True, "product": data}
