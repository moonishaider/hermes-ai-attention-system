"""Action proposal creation, shadowing, and approval validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .domain import ActionProposal, ActionState, RiskClass
from .policy import PolicyDecision, PolicyEngine
from .storage import Store


class ActionController:
    def __init__(self, store: Store, policy: PolicyEngine) -> None:
        self.store = store
        self.policy = policy

    def propose(
        self,
        *,
        action_type: str,
        context_id: str,
        risk_class: RiskClass,
        target: dict,
        payload: dict,
        evidence_ids: tuple[str, ...] = (),
        browser_profile: str | None = None,
        ttl_minutes: int = 15,
        idempotency_key: str | None = None,
    ) -> ActionProposal:
        now = datetime.now(UTC)
        proposal = ActionProposal.create(
            proposal_id=str(uuid4()),
            action_type=action_type,
            context_id=context_id,
            risk_class=risk_class,
            target=target,
            payload=payload,
            evidence_ids=evidence_ids,
            idempotency_key=idempotency_key or str(uuid4()),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=max(1, min(ttl_minutes, 60)))).isoformat(),
            browser_profile=browser_profile,
        )
        self.store.save_action(proposal)
        self.store.audit(
            "hermes",
            "action.propose",
            context_id,
            "success",
            {"proposal_id": proposal.proposal_id, "risk_class": risk_class, "preview_hash": proposal.preview_hash},
        )
        return proposal

    def shadow(self, proposal: ActionProposal) -> tuple[ActionProposal, PolicyDecision]:
        decision = self.policy.validate_proposal(proposal)
        shadowed = replace(proposal, state=ActionState.SHADOWED if decision.allowed else ActionState.BLOCKED)
        self.store.set_action_state(proposal.proposal_id, shadowed.state)
        return shadowed, decision

    def verify_approval(
        self,
        proposal: ActionProposal,
        *,
        approved_preview_hash: str,
        approval_identity: str,
    ) -> PolicyDecision:
        if approved_preview_hash != proposal.preview_hash:
            return PolicyDecision(False, "approved preview does not match proposal", "approval-hash-mismatch")
        if approval_identity != "Syed Moonis Haider":
            return PolicyDecision(False, "approval identity is not the configured owner", "approval-identity")
        decision = self.policy.validate_proposal(proposal)
        if decision.allowed:
            self.store.set_action_state(proposal.proposal_id, ActionState.APPROVED)
        return decision
