from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.OrderModel import OrderModel
from src.schemas.ToolSchemas import ToolDefinition, ToolExecutionContext
from src.tools.ToolInterface import ToolInterface
from src.tools.orders.OrderToolHelpers import serialize_order_details


class OrderCancellationTool(ToolInterface):
    """Cancel an owned order and restore its stock once."""

    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="order_cancellation",
            description=(
                "Cancel a pending or confirmed order owned by the authenticated "
                "customer and restore its product stock. Explicit confirmation is required."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "order_number": {"type": "string", "minLength": 1},
                },
                "required": ["order_number"],
                "additionalProperties": False,
            },
            requires_authentication=True,
            requires_confirmation=True,
            is_idempotent=True,
            tags=("orders", "cancel", "write_action"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        context = arguments.pop("_tool_context", None)
        if not isinstance(context, ToolExecutionContext) or context.user_id is None:
            raise ValueError("Authenticated customer context is required.")

        with self.session_factory() as session:
            order, already_cancelled = OrderModel.cancel_for_customer_id(
                session,
                order_number=arguments["order_number"],
                customer_id=context.user_id,
            )
            if order is None:
                return {
                    "found": False,
                    "cancelled": False,
                    "already_cancelled": False,
                    "order": None,
                }
            return {
                "found": True,
                "cancelled": True,
                "already_cancelled": already_cancelled,
                "order": serialize_order_details(order),
            }
