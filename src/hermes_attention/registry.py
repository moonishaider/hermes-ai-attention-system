"""Registry-driven specialists and external source adapter definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ConfigurationError, load_json


@dataclass(frozen=True, slots=True)
class Specialist:
    specialist_id: str
    version: str
    status: str
    contexts: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    prohibited_tools: tuple[str, ...]
    memory_namespace: str
    model_route: str
    serious_mode: bool
    path: Path


class SpecialistRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        configuration = load_json(root / "registry.json")
        self.specialists: dict[str, Specialist] = {}
        for item in configuration.get("specialists", []):
            path = (root / item["path"]).resolve()
            if root.resolve() not in path.parents:
                raise ConfigurationError(f"specialist path escapes registry: {path}")
            self.specialists[item["id"]] = Specialist(
                specialist_id=item["id"],
                version=item["version"],
                status=item["status"],
                contexts=tuple(item["contexts"]),
                allowed_tools=tuple(item["allowed_tools"]),
                prohibited_tools=tuple(item["prohibited_tools"]),
                memory_namespace=item["memory_namespace"],
                model_route=item["model_route"],
                serious_mode=bool(item.get("serious_mode", False)),
                path=path,
            )

    def activate(self, specialist_id: str, context_id: str) -> Specialist:
        specialist = self.specialists[specialist_id]
        if specialist.status != "active":
            raise PermissionError(f"specialist {specialist_id} is {specialist.status}")
        if "*" not in specialist.contexts and context_id not in specialist.contexts:
            raise PermissionError(f"specialist {specialist_id} cannot access {context_id}")
        return specialist


class IntegrationRegistry:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.connections = {item["id"]: item for item in configuration.get("external_sources", [])}

    def tool_inventory(self, connection_id: str) -> dict[str, list[str] | str]:
        connection = self.connections[connection_id]
        return {
            "mode": connection["mode"],
            "include": list(connection.get("tools", {}).get("include", [])),
            "exclude": list(connection.get("tools", {}).get("exclude", [])),
        }

    def assert_tool(self, connection_id: str, tool_name: str) -> None:
        connection = self.connections[connection_id]
        include = set(connection.get("tools", {}).get("include", []))
        exclude = set(connection.get("tools", {}).get("exclude", []))
        if tool_name in exclude or (include and tool_name not in include):
            raise PermissionError(f"tool {tool_name} is not exposed by {connection_id}")
