"""Deterministic tool and action policy independent of model output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .domain import ActionProposal, RiskClass, stable_hash


WRITE_VERBS = {
    "send",
    "create",
    "update",
    "delete",
    "post",
    "publish",
    "merge",
    "push",
    "upload",
    "submit",
    "purchase",
    "pay",
    "transfer",
    "invite",
    "approve",
}


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    code: str


class PolicyEngine:
    def __init__(self, *, external_writes_enabled: bool = False) -> None:
        self.external_writes_enabled = external_writes_enabled
        self.kill_switch = False

    @staticmethod
    def tool_is_mutating(tool_name: str) -> bool:
        tokens = tool_name.casefold().replace("-", "_").split("_")
        return any(token in WRITE_VERBS for token in tokens)

    def allow_external_tool(self, connection_mode: str, tool_name: str) -> PolicyDecision:
        if self.kill_switch:
            return PolicyDecision(False, "global action kill switch is active", "kill-switch")
        if connection_mode == "read-only" and self.tool_is_mutating(tool_name):
            return PolicyDecision(False, "write-capable tool is absent from a read-only connection", "readonly-tool")
        return PolicyDecision(True, "tool permitted by connection mode", "allowed")

    def validate_proposal(self, proposal: ActionProposal, *, now: datetime | None = None) -> PolicyDecision:
        now = now or datetime.now(UTC)
        if self.kill_switch:
            return PolicyDecision(False, "global action kill switch is active", "kill-switch")
        if proposal.context_id in {"unknown", "mixed"} and proposal.risk_class not in {RiskClass.A0, RiskClass.A1}:
            return PolicyDecision(False, "mixed or unknown context cannot perform an external action", "ambiguous-context")
        if proposal.risk_class is RiskClass.A4:
            return PolicyDecision(False, "A4 actions are manual-only", "manual-only")
        if proposal.risk_class in {RiskClass.A2, RiskClass.A3} and not self.external_writes_enabled:
            return PolicyDecision(False, "external execution is disabled; proposal/shadow mode only", "shadow-only")
        expires = datetime.fromisoformat(proposal.expires_at)
        if expires <= now:
            return PolicyDecision(False, "approval proposal has expired", "expired")
        expected_hash = stable_hash(
            {
                "action_type": proposal.action_type,
                "context_id": proposal.context_id,
                "risk_class": proposal.risk_class,
                "target": proposal.target,
                "payload": proposal.payload,
                "browser_profile": proposal.browser_profile,
            }
        )
        if expected_hash != proposal.preview_hash:
            return PolicyDecision(False, "payload or target changed after preview", "preview-mismatch")
        return PolicyDecision(True, "proposal satisfies deterministic policy", "allowed")

    def activate_kill_switch(self) -> None:
        self.kill_switch = True

    def reset_kill_switch(self) -> None:
        self.kill_switch = False
