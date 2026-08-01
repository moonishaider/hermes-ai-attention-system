"""Deterministic provenance-first context classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import ContextLabel, Provenance


CLASSIFIER_VERSION = "rules-v1"


@dataclass(frozen=True, slots=True)
class ContextRule:
    field: str
    value: str
    context_id: str
    confidence: float = 1.0
    operator: str = "equals"


class ContextRouter:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.contexts = {item["id"]: item for item in configuration.get("contexts", [])}
        self.rules: list[ContextRule] = []
        for context in configuration.get("contexts", []):
            for rule in context.get("rules", []):
                operator = "contains" if "contains" in rule else "equals"
                self.rules.append(
                    ContextRule(
                        field=rule["field"],
                        value=str(rule[operator]),
                        context_id=context["id"],
                        confidence=float(rule.get("weight", 1.0)),
                        operator=operator,
                    )
                )
        for rule in configuration.get("rules", []):
            self.rules.append(
                ContextRule(
                    field=rule["field"], value=str(rule["equals"]),
                    context_id=rule["context_id"], confidence=float(rule.get("confidence", 1.0))
                )
            )

    @staticmethod
    def _field(provenance: Provenance, name: str) -> str | None:
        if name.startswith("metadata."):
            value = provenance.metadata.get(name.partition(".")[2])
            return str(value) if value is not None else None
        value = getattr(provenance, name, None)
        return str(value) if value is not None else None

    def classify(self, provenance: Provenance, *, hints: tuple[str, ...] = ()) -> tuple[ContextLabel, ...]:
        labels: dict[str, ContextLabel] = {}
        for rule in self.rules:
            value = self._field(provenance, rule.field)
            matched = bool(value) and (
                value.casefold() == rule.value.casefold()
                if rule.operator == "equals"
                else rule.value.casefold() in value.casefold()
            )
            if matched:
                labels[rule.context_id] = ContextLabel(
                    context_id=rule.context_id,
                    confidence=rule.confidence,
                    reason=f"deterministic {rule.field} mapping",
                    classifier_version=CLASSIFIER_VERSION,
                )
        for hint in hints:
            if hint in self.contexts and hint not in labels:
                labels[hint] = ContextLabel(
                    context_id=hint,
                    confidence=0.65,
                    reason="explicit ingestion hint awaiting confirmation",
                    classifier_version=CLASSIFIER_VERSION,
                )
        if len(labels) > 1:
            return tuple(labels.values()) + (
                ContextLabel("mixed", 1.0, "multiple valid context labels", CLASSIFIER_VERSION),
            )
        if labels:
            return tuple(labels.values())
        return (ContextLabel("unknown", 1.0, "no deterministic mapping", CLASSIFIER_VERSION),)

    def browser_profile(self, context_id: str) -> str | None:
        context = self.contexts.get(context_id, {})
        profile = context.get("browser_profile")
        return str(profile) if profile else None
