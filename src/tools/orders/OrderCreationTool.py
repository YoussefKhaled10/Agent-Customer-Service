from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.OrderModel import OrderModel
from src.schemas.ToolSchemas import ToolDefinition, ToolExecutionContext
from src.tools.ToolInterface import ToolInterface
from src.tools.orders.OrderToolHelpers import serialize_order_details


class OrderCreationTool(ToolInterface):
    """Create an order for the authenticated customer."""

    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="order_creation",
            description=(
                "Create a new order for the authenticated customer using current "
                "database prices and stock. This action requires explicit confirmation."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "integer", "minimum": 1},
                                "quantity": {"type": "integer", "minimum": 1},
                            },
                            "required": ["product_id", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                    "shipping_address": {"type": "string", "minLength": 1},
                    "customer_notes": {"type": "string", "maxLength": 1000},
                    "idempotency_key": {"type": "string", "minLength": 8},
                },
                "required": ["items", "idempotency_key"],
                "additionalProperties": False,
            },
            requires_authentication=True,
            requires_confirmation=True,
            is_idempotent=True,
            tags=("orders", "create", "write_action"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        context = arguments.pop("_tool_context", None)
        if not isinstance(context, ToolExecutionContext) or context.user_id is None:
            raise ValueError("Authenticated customer context is required.")

        with self.session_factory() as session:
            order = OrderModel.create_for_customer_id(
                session,
                customer_id=context.user_id,
                items=arguments["items"],
                shipping_address=arguments.get("shipping_address"),
                customer_notes=arguments.get("customer_notes"),
                idempotency_key=arguments["idempotency_key"],
            )
            return {
                "created": True,
                "order": serialize_order_details(order),
            }
