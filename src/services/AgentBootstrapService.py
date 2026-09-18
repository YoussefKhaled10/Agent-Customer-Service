from __future__ import annotations

from src.services.AgentService import AgentService
from src.services.RAGService import RAGService
from src.services.ToolBootstrapService import ToolBootstrapService
from src.services.ToolExecutionService import ToolExecutionService


class AgentBootstrapService:
    @staticmethod
    def create_agent_service(
        *,
        rag_service: RAGService | None = None,
    ) -> AgentService:
        active_rag_service = rag_service or RAGService()
        registry = ToolBootstrapService.create_registry(
            rag_service=active_rag_service,
        )
        return AgentService(
            tool_registry=registry,
            tool_execution_service=ToolExecutionService(
                registry
            ),
            persistence_enabled=True,
        )
