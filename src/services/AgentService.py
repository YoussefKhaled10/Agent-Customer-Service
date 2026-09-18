from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from src.agent.AgentGraph import AgentGraph
from src.agent.AgentNodes import AgentNodes
from src.helpers.config import settings
from src.schemas.AgentSchemas import AgentChatResponse
from src.schemas.ToolSchemas import ToolExecutionRequest
from src.services.ConversationService import ConversationService
from src.services.PendingActionService import PendingActionService
from src.services.ToolAuditService import ToolAuditService
from src.services.ToolExecutionService import ToolExecutionService
from src.stores.llm.AnswerProviderFactory import AnswerProviderFactory
from src.stores.llm.AnswerProviderInterface import AnswerProviderInterface


class AgentService:
    def __init__(
        self,
        *,
        tool_registry: Any,
        decision_provider: AnswerProviderInterface | None = None,
        tool_execution_service: ToolExecutionService | None = None,
        graph: Any | None = None,
        persistence_enabled: bool = False,
        conversation_service: ConversationService | None = None,
        audit_service: ToolAuditService | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.executor = (
            tool_execution_service
            or ToolExecutionService(tool_registry)
        )
        provider = (
            decision_provider
            or AnswerProviderFactory.create(
                settings.AGENT_PROVIDER,
                model=settings.AGENT_MODEL,
            )
        )
        self.graph = graph or AgentGraph(
            AgentNodes(
                provider,
                self.executor,
                tool_registry,
            )
        ).build()
        self.persistence_enabled = persistence_enabled
        self.conversations = (
            conversation_service or ConversationService()
        )
        self.audit = audit_service or ToolAuditService()

    def chat(
        self,
        *,
        message: str,
        session_id: str,
        customer_id: int | None = None,
        conversation_messages: list[dict[str, str]] | None = None,
    ) -> AgentChatResponse:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("message cannot be empty.")

        conversation_id = None
        user_message_id = None
        pending_action = None
        history = conversation_messages or []

        if self.persistence_enabled:
            loaded = self.conversations.load_or_create(
                session_id=session_id,
                customer_id=customer_id,
            )
            conversation_id = loaded["conversation_id"]
            history = loaded["history"]
            pending_action = loaded["pending_action"]
            user_message_id = self.conversations.add_user_message(
                conversation_id,
                cleaned,
            )

        if pending_action:
            return self._handle_pending_action(
                message=cleaned,
                session_id=session_id,
                customer_id=customer_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                pending_action=pending_action,
            )

        state = self.graph.invoke(
            {
                "session_id": session_id,
                "request_id": f"agent-{uuid4()}",
                "conversation_id": conversation_id,
                "user_message": cleaned,
                "customer_id": customer_id,
                "conversation_messages": history,
                "available_tools": self.tool_registry.model_schemas(),
                "tool_results": [],
                "pending_action": None,
                "iteration_count": 0,
                "max_iterations": settings.AGENT_MAX_TOOL_ITERATIONS,
                "tool_arguments": {},
                "requires_confirmation": False,
            }
        )

        response = self._response_from_state(
            state,
            session_id=session_id,
            customer_id=customer_id,
        )

        if self.persistence_enabled and conversation_id is not None:
            pending = state.get("pending_action")
            if state.get("requires_confirmation") and pending:
                self.conversations.set_pending_action(
                    conversation_id,
                    pending,
                )
                response.response = (
                    PendingActionService.confirmation_message(
                        pending
                    )
                )
            self._persist_result(
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                response=response,
            )

        return response

    def _handle_pending_action(
        self,
        *,
        message: str,
        session_id: str,
        customer_id: int | None,
        conversation_id: int | None,
        user_message_id: int | None,
        pending_action: dict[str, Any],
    ) -> AgentChatResponse:
        decision = PendingActionService.classify(message)

        if decision == "reject":
            if conversation_id is not None:
                self.conversations.set_pending_action(
                    conversation_id,
                    None,
                )
            response = AgentChatResponse(
                session_id=session_id,
                decision_type="direct_response",
                response=(
                    "تمام، ألغيت العملية المعلقة ومفيش "
                    "أي تغيير اتنفذ."
                ),
                customer_authenticated=customer_id is not None,
            )
            self._save_assistant(conversation_id, response)
            return response

        if decision == "modify":
            response = AgentChatResponse(
                session_id=session_id,
                decision_type="clarification",
                response=(
                    "تمام، ابعت الطلب بالتفاصيل الجديدة كاملة "
                    "عشان أجهزه وأطلب تأكيدك من جديد."
                ),
                requires_clarification=True,
                requires_confirmation=True,
                customer_authenticated=customer_id is not None,
            )
            self._save_assistant(conversation_id, response)
            return response

        if decision != "confirm":
            response = AgentChatResponse(
                session_id=session_id,
                decision_type="clarification",
                response=PendingActionService.confirmation_message(
                    pending_action
                ),
                requires_clarification=True,
                requires_confirmation=True,
                customer_authenticated=customer_id is not None,
            )
            self._save_assistant(conversation_id, response)
            return response

        raw = self.executor.execute(
            ToolExecutionRequest(
                tool_name=pending_action["tool_name"],
                arguments=pending_action.get("arguments", {}),
                request_id=(
                    pending_action.get("request_id")
                    or f"confirm-{uuid4()}"
                ),
                user_id=customer_id,
                confirmed=True,
                metadata={"session_id": session_id},
            )
        )
        result = asdict(raw)

        if conversation_id is not None:
            self.conversations.set_pending_action(
                conversation_id,
                None,
            )
            self.audit.record(
                conversation_id=conversation_id,
                message_id=user_message_id,
                result=result,
                input_json={
                    "arguments": pending_action.get(
                        "arguments", {}
                    ),
                    "confirmed": True,
                },
            )

        response_text = (
            raw.message
            or (
                "تم تنفيذ العملية بنجاح."
                if raw.success
                else "مقدرتش أنفذ العملية. حاول تاني."
            )
        )
        if raw.success and isinstance(raw.data, dict):
            order = raw.data.get("order")
            if isinstance(order, dict) and order.get("order_number"):
                response_text = (
                    "تم تنفيذ العملية بنجاح. رقم الطلب: "
                    f"{order['order_number']}"
                )

        response = AgentChatResponse(
            session_id=session_id,
            decision_type="direct_response",
            response=response_text,
            tool_results=[result],
            customer_authenticated=customer_id is not None,
            error=None if raw.success else raw.error_code,
        )
        self._save_assistant(conversation_id, response)
        return response

    def _response_from_state(
        self,
        state: dict[str, Any],
        *,
        session_id: str,
        customer_id: int | None,
    ) -> AgentChatResponse:
        decision_type = state.get("decision_type", "error")
        return AgentChatResponse(
            session_id=session_id,
            decision_type=decision_type,
            response=(
                state.get("final_response")
                or "No response was generated."
            ),
            selected_tool=state.get("selected_tool"),
            tool_arguments=state.get("tool_arguments", {}),
            tool_results=state.get("tool_results", []),
            requires_tool_execution=False,
            requires_clarification=(
                decision_type == "clarification"
            ),
            requires_confirmation=state.get(
                "requires_confirmation", False
            ),
            customer_authenticated=customer_id is not None,
            error=(
                "agent_generation_unavailable"
                if state.get("error")
                else None
            ),
        )

    def _persist_result(
        self,
        *,
        conversation_id: int,
        user_message_id: int | None,
        response: AgentChatResponse,
    ) -> None:
        for result in response.tool_results:
            self.audit.record(
                conversation_id=conversation_id,
                message_id=user_message_id,
                result=result,
                input_json={
                    "tool_name": result.get("tool_name")
                },
            )
        self._save_assistant(conversation_id, response)

    def _save_assistant(
        self,
        conversation_id: int | None,
        response: AgentChatResponse,
    ) -> None:
        if conversation_id is None:
            return
        self.conversations.add_assistant_message(
            conversation_id,
            response.response,
            metadata={
                "requires_confirmation": (
                    response.requires_confirmation
                ),
                "tool_names": [
                    result.get("tool_name")
                    for result in response.tool_results
                ],
            },
        )
