from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.CustomerModel import CustomerModel
from src.models.Database import database_session
from src.models.InquiryModel import InquiryModel
from src.models.PharmacistRequestModel import PharmacistRequestModel
from src.models.db_schemes.agent_db.enums import ContactMethod, InquiryPriority
from src.schemas.ToolSchemas import ToolDefinition, ToolExecutionContext
from src.tools.ToolInterface import ToolInterface


class HumanHandoffTool(ToolInterface):
    """Create an existing customer inquiry or pharmacist request."""

    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="human_handoff",
            description=(
                "Escalate an authenticated customer to human review. Use route "
                "'support' for order, payment, product, technical, or complaint "
                "issues. Use route 'pharmacist' when a licensed pharmacist should "
                "review a product or medication-related question."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "route": {
                        "type": "string",
                        "enum": ["support", "pharmacist"],
                    },
                    "subject": {
                        "type": "string",
                        "minLength": 3,
                        "maxLength": 250,
                    },
                    "summary": {
                        "type": "string",
                        "minLength": 5,
                        "maxLength": 2000,
                    },
                    "priority": {
                        "type": "string",
                        "enum": [item.value for item in InquiryPriority],
                    },
                    "related_product_id": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "preferred_contact_method": {
                        "type": "string",
                        "enum": [item.value for item in ContactMethod],
                    },
                },
                "required": ["route", "subject", "summary"],
                "additionalProperties": False,
            },
            requires_authentication=True,
            requires_confirmation=False,
            is_idempotent=False,
            tags=("support", "pharmacist", "human_handoff", "write_action"),
        )

    def execute(self, **arguments: Any) -> dict[str, Any]:
        context = arguments.pop("_tool_context", None)
        if not isinstance(context, ToolExecutionContext) or context.user_id is None:
            raise ValueError("Authenticated customer context is required.")

        with self.session_factory() as session:
            customer = CustomerModel.get_by_id(session, context.user_id)
            if customer is None or not customer.is_active:
                return {
                    "handoff_created": False,
                    "reason": "authenticated_customer_not_found",
                    "request": None,
                }

            if arguments["route"] == "pharmacist":
                return self._create_pharmacist_request(
                    session=session,
                    customer=customer,
                    arguments=arguments,
                )

            return self._create_customer_inquiry(
                session=session,
                customer=customer,
                arguments=arguments,
            )

    @staticmethod
    def _create_customer_inquiry(
        *,
        session: Session,
        customer: Any,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        priority = InquiryPriority(
            arguments.get("priority", InquiryPriority.NORMAL.value)
        )
        inquiry = InquiryModel.create(
            session,
            customer_name=customer.name,
            email=customer.email,
            subject=arguments["subject"],
            content=arguments["summary"],
            phone=customer.phone,
            customer_id=customer.id,
            priority=priority,
        )
        return {
            "handoff_created": True,
            "route": "support",
            "request": {
                "inquiry_id": inquiry.id,
                "status": getattr(inquiry.status, "value", str(inquiry.status)),
                "priority": getattr(inquiry.priority, "value", str(inquiry.priority)),
                "subject": inquiry.subject,
            },
            "message": "The customer inquiry was created for human support review.",
        }

    @staticmethod
    def _create_pharmacist_request(
        *,
        session: Session,
        customer: Any,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if not customer.phone:
            raise ValueError(
                "A phone number must be saved on the customer profile before "
                "requesting pharmacist contact."
            )
        contact_method = ContactMethod(
            arguments.get("preferred_contact_method", ContactMethod.PHONE.value)
        )
        request = PharmacistRequestModel.create(
            session,
            customer_name=customer.name,
            phone=customer.phone,
            question_summary=(
                f"{arguments['subject']}: {arguments['summary']}"
            ),
            email=customer.email,
            customer_id=customer.id,
            related_product_id=arguments.get("related_product_id"),
            preferred_contact_method=contact_method,
        )
        return {
            "handoff_created": True,
            "route": "pharmacist",
            "request": {
                "pharmacist_request_id": request.id,
                "status": getattr(request.status, "value", str(request.status)),
                "preferred_contact_method": getattr(
                    request.preferred_contact_method,
                    "value",
                    str(request.preferred_contact_method),
                ),
                "related_product_id": request.related_product_id,
            },
            "message": (
                "The pharmacist contact request was created for human review. "
                "This does not guarantee immediate contact."
            ),
        }
