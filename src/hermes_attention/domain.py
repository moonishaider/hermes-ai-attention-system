"""Typed domain records shared across the Hermes attention core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


class ConfidenceState(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class RiskClass(StrEnum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


class ActionState(StrEnum):
    PROPOSED = "proposed"
    SHADOWED = "shadowed"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class Provenance:
    source_system: str
    connection_id: str
    source_id: str
    source_timestamp: str
    retrieved_at: str
    account_id: str | None = None
    workspace: str | None = None
    container: str | None = None
    author: str | None = None
    uri: str | None = None
    revision: str | None = None
    permission_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        return stable_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class ContextLabel:
    context_id: str
    confidence: float
    reason: str
    classifier_version: str
    corrected_by_user: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("context confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    title: str
    content: str
    provenance: Provenance
    contexts: tuple[ContextLabel, ...]
    sensitivity: str = "private"
    confidence_state: ConfidenceState = ConfidenceState.INFERRED
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if not self.content_hash:
            object.__setattr__(self, "content_hash", sha256(self.content.encode("utf-8")).hexdigest())


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    title: str
    context_id: str
    task_type: str
    status: str = "triage"
    priority: int = 50
    owner: str = "Syed"
    waiting_on: str | None = None
    due_at: str | None = None
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class ActionProposal:
    proposal_id: str
    action_type: str
    context_id: str
    risk_class: RiskClass
    target: dict[str, Any]
    payload: dict[str, Any]
    evidence_ids: tuple[str, ...]
    idempotency_key: str
    created_at: str
    expires_at: str
    preview_hash: str
    browser_profile: str | None = None
    state: ActionState = ActionState.PROPOSED

    @classmethod
    def create(
        cls,
        *,
        proposal_id: str,
        action_type: str,
        context_id: str,
        risk_class: RiskClass,
        target: dict[str, Any],
        payload: dict[str, Any],
        evidence_ids: tuple[str, ...],
        idempotency_key: str,
        created_at: str,
        expires_at: str,
        browser_profile: str | None = None,
    ) -> "ActionProposal":
        preview_hash = stable_hash(
            {
                "action_type": action_type,
                "context_id": context_id,
                "risk_class": risk_class,
                "target": target,
                "payload": payload,
                "browser_profile": browser_profile,
            }
        )
        return cls(
            proposal_id=proposal_id,
            action_type=action_type,
            context_id=context_id,
            risk_class=risk_class,
            target=target,
            payload=payload,
            evidence_ids=evidence_ids,
            idempotency_key=idempotency_key,
            created_at=created_at,
            expires_at=expires_at,
            preview_hash=preview_hash,
            browser_profile=browser_profile,
        )
