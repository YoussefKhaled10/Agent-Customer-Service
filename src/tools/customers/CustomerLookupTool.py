from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.CustomerModel import CustomerModel
from src.models.Database import database_session
from src.schemas.ToolSchemas import ToolDefinition, ToolExecutionContext
from src.tools.ToolInterface import ToolInterface


class CustomerLookupTool(ToolInterface):
    """Return the authenticated customer's own profile."""

    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="customer_lookup",
            description=(
                "Get the authenticated customer's own PharmaCare profile. "
                "Use this tool for 'my account', contact details, and default "
                "shipping address questions. It cannot access another customer."
            ),
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            requires_authentication=True,
            requires_confirmation=False,
            is_idempotent=True,
            tags=("customers", "profile", "sensitive_read"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        context = arguments.pop("_tool_context", None)
        if not isinstance(context, ToolExecutionContext) or context.user_id is None:
            raise ValueError("Authenticated customer context is required.")

        with self.session_factory() as session:
            customer = CustomerModel.get_by_id(session, context.user_id)
            if customer is None:
                return {"found": False, "customer": None}

            return {
                "found": True,
                "customer": {
                    "customer_id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "default_shipping_address": customer.default_shipping_address,
                    "is_active": customer.is_active,
                },
            }
