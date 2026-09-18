from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ProductModel import ProductModel
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface


class InventoryCheckTool(ToolInterface):
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="inventory_check",
            description=(
                "Check available stock for an active product and whether a requested "
                "quantity can be fulfilled. Use product_id or SKU, but not both."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "minimum": 1},
                    "sku": {"type": "string", "minLength": 1},
                    "quantity": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            requires_authentication=False,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("products", "inventory", "read_only"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        product_id = arguments.get("product_id")
        sku = str(arguments.get("sku", "")).strip() or None
        quantity = arguments.get("quantity", 1)
        if (product_id is None) == (sku is None):
            raise ValueError("Provide exactly one of product_id or sku.")

        with self.session_factory() as session:
            product = (
                ProductModel.get_by_id(session, product_id)
                if product_id is not None
                else ProductModel.get_by_sku(session, sku)
            )
            if product is None or not product.is_active:
                return {
                    "found": False,
                    "available": False,
                    "can_fulfill": False,
                    "product": None,
                }
            available_stock = product.available_stock
            result = {
                "found": True,
                "available": available_stock > 0,
                "can_fulfill": available_stock >= quantity,
                "requested_quantity": quantity,
                "available_stock": available_stock,
                "product": {
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "is_active": product.is_active,
                },
            }

        return result
