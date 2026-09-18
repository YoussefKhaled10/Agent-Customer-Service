from __future__ import annotations

from collections.abc import Iterable

from src.exceptions.ToolExceptions import (
    ToolNotFoundError,
    ToolRegistrationError,
)
from src.schemas.ToolSchemas import ToolDefinition
from src.tools.ToolInterface import ToolInterface


class ToolRegistry:
    """Store, discover, and resolve tools by their unique names."""

    def __init__(self, tools: Iterable[ToolInterface] | None = None) -> None:
        self._tools: dict[str, ToolInterface] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: ToolInterface) -> None:
        if not isinstance(tool, ToolInterface):
            raise ToolRegistrationError(
                "Registered tools must implement ToolInterface."
            )

        name = tool.definition.name.strip()
        if not name:
            raise ToolRegistrationError("Tool name cannot be empty.")
        if name in self._tools:
            raise ToolRegistrationError(
                f"Tool '{name}' is already registered."
            )

        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        normalized_name = name.strip()
        if normalized_name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{normalized_name}' is not registered."
            )
        del self._tools[normalized_name]

    def get(self, name: str) -> ToolInterface:
        normalized_name = name.strip()
        try:
            return self._tools[normalized_name]
        except KeyError as error:
            raise ToolNotFoundError(
                f"Tool '{normalized_name}' is not registered."
            ) from error

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def model_schemas(self) -> list[dict]:
        return [definition.to_model_schema() for definition in self.definitions()]

    def names(self) -> list[str]:
        return list(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
