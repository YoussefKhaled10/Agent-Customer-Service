from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.schemas.ToolSchemas import ToolDefinition


class ToolInterface(ABC):
    """Contract that every agent tool must implement."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the metadata and JSON input schema exposed to the agent."""

    @abstractmethod
    def execute(self, **arguments: Any) -> Any:
        """Execute validated arguments and return JSON-serializable data."""
