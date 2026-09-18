from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, ContextManager

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import (
    InquiryStatus,
    PharmacistRequestStatus,
    ToolExecutionStatus,
)
from src.models.db_schemes.agent_db.schemes.conversation import Conversation
from src.models.db_schemes.agent_db.schemes.customer import Customer
from src.models.db_schemes.agent_db.schemes.customer_inquiry import CustomerInquiry
from src.models.db_schemes.agent_db.schemes.knowledge import KnowledgeChunk, KnowledgeDocument
from src.models.db_schemes.agent_db.schemes.order import Order
from src.models.db_schemes.agent_db.schemes.pharmacist_request import PharmacistRequest
from src.models.db_schemes.agent_db.schemes.product import Product
from src.models.db_schemes.agent_db.schemes.tool_execution import ToolExecution


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    metrics: dict[str, Any]
    recent_orders: list[dict[str, Any]]
    knowledge_documents: list[dict[str, Any]]
    tool_success_rate: float
    agent_requests: int


class AdminDashboardService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def get_overview(self) -> DashboardOverview:
        with self.session_factory() as session:
            metrics = {
                "products": self._count(session, Product),
                "customers": self._count(session, Customer),
                "orders": self._count(session, Order),
                "open_inquiries": self._count_where(
                    session,
                    CustomerInquiry,
                    CustomerInquiry.status == InquiryStatus.OPEN,
                ),
                "pharmacist_requests": self._count_where(
                    session,
                    PharmacistRequest,
                    PharmacistRequest.status == PharmacistRequestStatus.PENDING,
                ),
                "rag_documents": self._count(session, KnowledgeDocument),
                "rag_chunks": self._count(session, KnowledgeChunk),
                "pending_actions": self._count_where(
                    session,
                    Conversation,
                    Conversation.pending_action.is_not(None),
                ),
            }
            executions = session.execute(
                select(
                    func.count(ToolExecution.id),
                    func.sum(
                        case(
                            (
                                ToolExecution.status == ToolExecutionStatus.SUCCESS,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                )
            ).one()
            total_executions = int(executions[0] or 0)
            successful = int(executions[1] or 0)
            success_rate = round(
                successful / total_executions * 100,
                1,
            ) if total_executions else 0.0

            order_rows = session.scalars(
                select(Order)
                .options(joinedload(Order.customer))
                .order_by(Order.created_at.desc())
                .limit(5)
            ).all()
            recent_orders = [
                {
                    "order_number": order.order_number,
                    "customer_name": order.customer.name,
                    "status": order.status.value,
                    "total": f"{Decimal(order.total_amount):,.2f}",
                    "currency": order.currency,
                    "created_at": order.created_at,
                }
                for order in order_rows
            ]

            documents = session.scalars(
                select(KnowledgeDocument)
                .order_by(KnowledgeDocument.updated_at.desc())
                .limit(5)
            ).all()
            knowledge_documents = [
                {
                    "id": document.id,
                    "title": document.title,
                    "category": document.category.value,
                    "chunk_count": len(document.chunks),
                    "status": document.index_status.value,
                    "is_active": document.is_active,
                    "updated_at": document.updated_at,
                }
                for document in documents
            ]

        return DashboardOverview(
            metrics=metrics,
            recent_orders=recent_orders,
            knowledge_documents=knowledge_documents,
            tool_success_rate=success_rate,
            agent_requests=total_executions,
        )

    @staticmethod
    def _count(session: Session, model: type[Any]) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    @staticmethod
    def _count_where(
        session: Session,
        model: type[Any],
        condition: Any,
    ) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(model).where(condition)
            )
            or 0
        )
