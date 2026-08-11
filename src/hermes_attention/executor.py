"""Destination-locked supervised executor, deliberately absent from Hermes tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
import sqlite3
from typing import Callable, Any
from uuid import uuid4

from .daily_report import DailyReportLock, validate_daily_report_payload
from .domain import ActionProposal, ActionState
from .policy import PolicyEngine
from .storage import Store


class ExecutionDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class SlackDestination:
    workspace_id: str
    channel_id: str

    @classmethod
    def from_lock(cls, lock: DailyReportLock) -> "SlackDestination":
        return cls(lock.workspace_id, lock.channel_id)


class SupervisedActionExecutor:
    """Executes only one exact approved daily-report action through an injected sender."""

    def __init__(self, store: Store, policy: PolicyEngine, destination: SlackDestination, *, sender: Callable[[str, str], dict[str, Any]], lock: DailyReportLock | None = None) -> None:
        self.store = store
        self.policy = policy
        self.destination = destination
        self.sender = sender
        self.lock = lock

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
        try:
            text = validate_daily_report_payload(proposal.payload, self.lock) if self.lock else str(proposal.payload.get("text", ""))
        except ValueError as exc:
            raise ExecutionDenied(str(exc)) from exc
        if not text.strip():
            raise ExecutionDenied("daily report text is required")
        decision = self.policy.validate_proposal(proposal)
        if not decision.allowed:
            raise ExecutionDenied(decision.reason)
        stored = self.store.get_action(proposal.proposal_id)
        if not stored or stored["state"] != ActionState.APPROVED:
            raise ExecutionDenied("proposal is not in approved state")
        attempt_id = str(uuid4())
        now = datetime.now(UTC)
        try:
            with self.store.connection:
                self.store.connection.execute(
                    "INSERT INTO action_attempts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        attempt_id,
                        proposal.proposal_id,
                        (now + timedelta(minutes=2)).isoformat(),
                        "leased",
                        None,
                        None,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ExecutionDenied("action already has an execution attempt; reconcile before retry") from exc
        try:
            response = self.sender(self.destination.channel_id, text)
        except Exception:
            # The provider may have accepted the write before a transport failure. Preserve an
            # uncertain receipt and refuse automatic replay until an owner reconciles it.
            with self.store.connection:
                self.store.connection.execute(
                    "UPDATE action_attempts SET state='uncertain',updated_at=? WHERE attempt_id=?",
                    (datetime.now(UTC).isoformat(), attempt_id),
                )
            raise
        result_hash = sha256(json.dumps(response, sort_keys=True, default=str).encode()).hexdigest()
        provider_id = str(response.get("ts") or response.get("id") or "") if isinstance(response, dict) else ""
        completed_at = datetime.now(UTC).isoformat()
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE action_attempts SET state='executed',provider_id=?,result_hash=?,updated_at=? WHERE attempt_id=?",
                (provider_id or None, result_hash, completed_at, attempt_id),
            )
            self.store.connection.execute(
                "UPDATE actions SET state=?,updated_at=? WHERE proposal_id=?",
                (ActionState.EXECUTED, completed_at, proposal.proposal_id),
            )
        self.store.audit("hermes-executor", "slack.daily-update.publish", "inside-success", "success", {"proposal_id": proposal.proposal_id, "channel_id": self.destination.channel_id})
        return {"executed": True, "proposal_id": proposal.proposal_id, "provider_receipt": bool(response)}


DISABLED_FUTURE_HOOKS = {
    "calendar_create": "disabled-preview-approval-required",
    "email_draft_create": "disabled-preview-approval-required",
    "email_send": "disabled-preview-approval-required",
    "isolated_download": "disabled-preview-approval-required",
    "personal_browser_task": "disabled-preview-approval-required",
}
