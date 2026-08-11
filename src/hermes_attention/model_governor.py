"""Deterministic model selection and real delegated-result execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from typing import Any
from uuid import uuid4

from .domain import utc_now
from .models import BudgetExceeded, ModelRouter
from .runtime_models import DirectModelClient, ModelRouteError
from .storage import Store


@dataclass(frozen=True, slots=True)
class ModelSignals:
    visual: bool = False
    source_count: int = 0
    context_count: int = 1
    difficult_reasoning: bool = False
    contradiction: bool = False
    ambiguous_attribution: bool = False
    high_stakes: bool = False
    evidence_complete: bool = True
    first_pass_confidence: float = 1.0
    user_override: str | None = None
    optional_background: bool = False


@dataclass(frozen=True, slots=True)
class ModelDecision:
    route: str
    reason: str
    escalation_route: str | None = None
    reviewer_route: str | None = None


class ModelGovernor:
    ALLOWED = {"routine", "difficult", "vision", "review"}

    def __init__(self, router: ModelRouter, store: Store) -> None:
        self.router = router
        self.store = store

    def decide(self, signals: ModelSignals) -> ModelDecision:
        if signals.user_override:
            if signals.user_override not in self.ALLOWED:
                raise ValueError("unsupported model override")
            return ModelDecision(signals.user_override, "explicit owner override")
        if signals.visual:
            return ModelDecision("vision", "visual input requires Luna")
        difficult = (
            signals.difficult_reasoning or signals.contradiction or signals.ambiguous_attribution
            or signals.source_count > 1 or signals.context_count > 1
            or not signals.evidence_complete or signals.first_pass_confidence < 0.72
        )
        if signals.high_stakes:
            return ModelDecision("difficult", "high-stakes synthesis", reviewer_route="review")
        if difficult:
            return ModelDecision("difficult", "complex, multi-source, ambiguous, or weak evidence")
        return ModelDecision("routine", "routine low-risk request")

    def execute(
        self, client: DirectModelClient, prompt: str, signals: ModelSignals,
        *, image_data_url: str | None = None, max_output_tokens: int = 256,
    ) -> dict[str, Any]:
        self.router.assert_budget(optional=signals.optional_background)
        decision = self.decide(signals)
        run_id = str(uuid4())
        started = time.monotonic()
        outcome = "failed"
        total_cost = 0.0
        result: dict[str, Any] = {}
        try:
            result = client.generate(
                decision.route, prompt, image_data_url=image_data_url,
                feature=f"governed:{decision.route}", max_output_tokens=max_output_tokens,
            )
            total_cost += float(result.get("estimated_cost_usd", 0))
            if not result.get("success"):
                raise ModelRouteError(str(result.get("error_class") or "route failed"))
            if decision.reviewer_route:
                reviewed = client.generate(
                    decision.reviewer_route,
                    "Independently review and correct this high-stakes answer. Preserve evidence labels; "
                    "state uncertainty and do not invent facts.\n\n" + str(result.get("text", "")),
                    feature="governed:review", max_output_tokens=max_output_tokens,
                )
                total_cost += float(reviewed.get("estimated_cost_usd", 0))
                if reviewed.get("success"):
                    result = reviewed
            outcome = "success"
            return {
                **result, "governor_run_id": run_id, "route": decision.route,
                "reason": decision.reason, "reviewer_route": decision.reviewer_route,
                "estimated_total_cost_usd": total_cost,
            }
        finally:
            with self.store.connection:
                self.store.connection.execute(
                    "INSERT INTO model_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        run_id, decision.route, decision.reason,
                        json.dumps(asdict(signals), sort_keys=True), signals.user_override,
                        decision.escalation_route, decision.reviewer_route,
                        round((time.monotonic() - started) * 1000), total_cost, outcome, utc_now(),
                    ),
                )
