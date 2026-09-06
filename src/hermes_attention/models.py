"""Configurable model-role routing and budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .storage import Store


@dataclass(frozen=True, slots=True)
class ModelRoute:
    route_id: str
    provider: str
    model: str
    purpose: str
    enabled: bool
    required_capabilities: tuple[str, ...]


class BudgetExceeded(RuntimeError):
    pass


class ModelRouter:
    def __init__(self, configuration: dict[str, Any], store: Store) -> None:
        self.store = store
        self.default_route = configuration["default_route"]
        route_items = configuration["routes"]
        iterable = route_items.items() if isinstance(route_items, dict) else ((item["id"], item) for item in route_items)
        self.routes = {
            route_id: ModelRoute(
                route_id=route_id,
                provider=item["provider"],
                model=item["model"],
                purpose=item["purpose"],
                enabled=bool(item.get("enabled", True)),
                required_capabilities=tuple(item.get("required_capabilities", item.get("capabilities", []))),
            )
            for route_id, item in iterable
        }
        budget = configuration.get("budget_usd", configuration.get("budget_usd_monthly", {}))
        self.soft_budget = float(budget["soft"])
        self.hard_budget = float(budget["hard"])

    def choose(self, *, modality: str = "text", stakes: str = "routine", complexity: str = "routine") -> ModelRoute:
        route_id = self.default_route
        if modality == "image":
            route_id = "vision"
        elif stakes == "high":
            route_id = "review"
        elif complexity == "difficult":
            route_id = "difficult"
        route = self.routes[route_id]
        if not route.enabled:
            fallback = self.routes[self.default_route]
            if not fallback.enabled:
                raise RuntimeError("no enabled model route")
            return fallback
        return route

    def assert_budget(self, *, optional: bool) -> float:
        month = datetime.now(UTC).strftime("%Y-%m")
        spent = self.store.monthly_cost(month)
        if spent >= self.hard_budget:
            raise BudgetExceeded(f"model work stopped at ${spent:.2f}")
        return spent

    def budget_status(self) -> dict[str, float | str]:
        month = datetime.now(UTC).strftime("%Y-%m")
        spent = self.store.monthly_cost(month)
        level = "hard-stop" if spent >= self.hard_budget else "warning" if spent >= self.soft_budget else "ok"
        return {"month": month, "spent_usd": spent, "soft_usd": self.soft_budget, "hard_usd": self.hard_budget, "level": level}
