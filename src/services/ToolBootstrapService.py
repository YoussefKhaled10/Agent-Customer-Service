from __future__ import annotations

from typing import Callable, ContextManager

from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.services.RAGService import RAGService
from src.tools.ToolRegistry import ToolRegistry
from src.tools.categories import CategoryListTool
from src.tools.customers import CustomerLookupTool
from src.tools.knowledge.KnowledgeRAGTool import KnowledgeRAGTool
from src.tools.orders import (
    CustomerOrdersTool,
    OrderCancellationTool,
    OrderCreationTool,
    OrderDetailsTool,
    OrderStatusTool,
)
from src.tools.products import (
    InventoryCheckTool,
    ProductDetailsTool,
    ProductSearchTool,
)
from src.tools.sales import SalesRecommendationTool
from src.tools.support import HumanHandoffTool


class ToolBootstrapService:
    @staticmethod
    def create_registry(
        *,
        rag_service: RAGService | None = None,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> ToolRegistry:
        return ToolRegistry(
            [
                KnowledgeRAGTool(rag_service=rag_service),
                CategoryListTool(session_factory=session_factory),
                ProductSearchTool(session_factory=session_factory),
                ProductDetailsTool(session_factory=session_factory),
                InventoryCheckTool(session_factory=session_factory),
                CustomerLookupTool(session_factory=session_factory),
                CustomerOrdersTool(session_factory=session_factory),
                OrderStatusTool(session_factory=session_factory),
                OrderDetailsTool(session_factory=session_factory),
                OrderCreationTool(session_factory=session_factory),
                OrderCancellationTool(session_factory=session_factory),
                SalesRecommendationTool(session_factory=session_factory),
                HumanHandoffTool(session_factory=session_factory),
            ]
        )
