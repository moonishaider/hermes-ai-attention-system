"""Destination-locked supervised executor, deliberately absent from Hermes tools."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable, Any

from .domain import ActionProposal, ActionState
from .policy import PolicyEngine
from .storage import Store


class ExecutionDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class SlackDestination:
    workspace_id: str
    channel_id: str


class SupervisedActionExecutor:
    """Executes only one exact approved daily-report action through an injected sender."""

    def __init__(self, store: Store, policy: PolicyEngine, destination: SlackDestination, *, sender: Callable[[str, str], dict[str, Any]]) -> None:
        self.store = store
        self.policy = policy
        self.destination = destination
        self.sender = sender

    def execute_daily_report(self, proposal: ActionProposal, *, approved_hash: str) -> dict[str, Any]:
        if os.environ.get("HERMES_ACTIONS_KILL_SWITCH", "1") != "0":
            raise ExecutionDenied("global action kill switch is active")
        if proposal.action_type != "publish_inside_success_daily_update" or proposal.context_id != "inside-success":
            raise ExecutionDenied("executor accepts only the fixed Inside Success daily update action")
        if approved_hash != proposal.preview_hash:
            raise ExecutionDenied("approved preview hash mismatch")
        target = proposal.target
        if target != {"workspace_id": self.destination.workspace_id, "channel_id": self.destination.channel_id}:
            raise ExecutionDenied("destination lock mismatch")
        decision = self.policy.validate_proposal(proposal)
        if not decision.allowed:
            raise ExecutionDenied(decision.reason)
        stored = self.store.get_action(proposal.proposal_id)
        if not stored or stored["state"] != ActionState.APPROVED:
            raise ExecutionDenied("proposal is not in approved state")
        response = self.sender(self.destination.channel_id, str(proposal.payload.get("text", "")))
        self.store.set_action_state(proposal.proposal_id, ActionState.EXECUTED)
        self.store.audit("hermes-executor", "slack.daily-update.publish", "inside-success", "success", {"proposal_id": proposal.proposal_id, "channel_id": self.destination.channel_id})
        return {"executed": True, "proposal_id": proposal.proposal_id, "provider_receipt": bool(response)}


DISABLED_FUTURE_HOOKS = {
    "calendar_create": "disabled-preview-approval-required",
    "email_draft_create": "disabled-preview-approval-required",
    "email_send": "disabled-preview-approval-required",
    "isolated_download": "disabled-preview-approval-required",
    "personal_browser_task": "disabled-preview-approval-required",
}
