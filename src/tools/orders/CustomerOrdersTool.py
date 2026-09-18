from __future__ import annotations

from typing import Any, Callable, ContextManager
from sqlalchemy.orm import Session
from src.models.Database import database_session
from src.models.OrderModel import OrderModel
from src.models.db_schemes.agent_db.enums import OrderStatus
from src.schemas.ToolSchemas import ToolDefinition, ToolExecutionContext
from src.tools.ToolInterface import ToolInterface
from src.tools.orders.OrderToolHelpers import serialize_order_summary


class CustomerOrdersTool(ToolInterface):
    def __init__(self, session_factory: Callable[[], ContextManager[Session]] = database_session) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="customer_orders",
            description="List recent orders belonging to the authenticated customer.",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": [item.value for item in OrderStatus]},
                    "limit": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            requires_authentication=True,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("orders", "list", "sensitive_read"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        context = arguments.pop("_tool_context", None)
        if not isinstance(context, ToolExecutionContext) or context.user_id is None:
            raise ValueError("Authenticated customer context is required.")
        raw_status = arguments.get("status")
        status = OrderStatus(raw_status) if raw_status else None
        with self.session_factory() as session:
            orders = OrderModel.list_by_customer_id(
                session,
                context.user_id,
                status=status,
                limit=arguments.get("limit", 20),
            )
            data = [serialize_order_summary(order) for order in orders]
        return {"count": len(data), "orders": data}
