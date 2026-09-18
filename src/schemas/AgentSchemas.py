from __future__ import annotations
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
DecisionType = Literal["tool_call", "direct_response", "clarification", "error"]
class AgentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_type: DecisionType
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
    clarification_question: str | None = None
    reason: str | None = None
    @model_validator(mode="after")
    def validate_payload(self):
        if self.decision_type == "tool_call" and not self.tool_name:
            raise ValueError("tool_name is required for tool_call.")
        if self.decision_type == "direct_response" and not self.response:
            raise ValueError("response is required for direct_response.")
        if self.decision_type == "clarification" and not self.clarification_question:
            raise ValueError("clarification_question is required.")
        return self
class AgentChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1,max_length=4000)
    session_id: str = Field(default_factory=lambda:str(uuid4()),min_length=1,max_length=255)
    @field_validator("message","session_id",mode="before")
    @classmethod
    def strip_text(cls,value:Any)->str: return str(value).strip()
class AgentChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    decision_type: DecisionType
    response: str
    selected_tool: str | None = None
    tool_arguments: dict[str,Any] = Field(default_factory=dict)
    tool_results: list[dict[str,Any]] = Field(default_factory=list)
    requires_tool_execution: bool = False
    requires_clarification: bool = False
    requires_confirmation: bool = False
    customer_authenticated: bool = False
    error: str | None = None
