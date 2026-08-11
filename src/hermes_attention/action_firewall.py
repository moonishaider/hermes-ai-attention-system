"""Deny-by-default capability firewall for any external write surface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hmac
import json
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .domain import stable_hash, utc_now
from .storage import Store


@dataclass(frozen=True, slots=True)
class FirewallDecision:
    allowed: bool
    code: str
    reason: str


class ActionFirewall:
    """A model cannot mint intent; only a trusted local owner interaction can."""

    def __init__(self, store: Store, signing_secret: bytes, *, global_kill_switch: bool = True) -> None:
        if len(signing_secret) < 32:
            raise ValueError("signing secret must contain at least 32 bytes")
        self.store = store
        self.signing_secret = signing_secret
        self.global_kill_switch = global_kill_switch

    def register_capability(
        self, *, capability_id: str, context_id: str, account_id: str,
        target_lock: dict[str, Any], permission_inventory: dict[str, Any],
        browser_profile: str | None = None, autonomy_stage: int = 0,
        reversible: bool = False, enabled: bool = False,
    ) -> None:
        if not 0 <= autonomy_stage <= 5:
            raise ValueError("invalid autonomy stage")
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO action_capabilities VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(capability_id) DO UPDATE SET target_lock_json=excluded.target_lock_json,
                   autonomy_stage=excluded.autonomy_stage,reversible=excluded.reversible,
                   enabled=excluded.enabled,permission_hash=excluded.permission_hash,
                   kill_switch=excluded.kill_switch,updated_at=excluded.updated_at""",
                (capability_id, context_id, account_id, browser_profile,
                 json.dumps(target_lock, sort_keys=True), autonomy_stage, int(reversible),
                 int(enabled), stable_hash(permission_inventory), 1, utc_now()),
            )

    def issue_owner_intent(
        self, *, session_nonce: str, action_type: str, request_text: str,
        trusted_local_interaction: bool, ttl_seconds: int = 120,
    ) -> str:
        if not trusted_local_interaction:
            raise PermissionError("retrieved content cannot authorize an action")
        intent_id = str(uuid4())
        now = datetime.now(UTC)
        request_hash = sha256(request_text.encode("utf-8")).hexdigest()
        expires = now + timedelta(seconds=max(10, min(ttl_seconds, 300)))
        payload = f"{intent_id}:{session_nonce}:{action_type}:{request_hash}:{expires.isoformat()}"
        signature = hmac.new(self.signing_secret, payload.encode(), sha256).hexdigest()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO owner_intents VALUES(?,?,?,?,?,?,NULL)",
                (intent_id, session_nonce, action_type, request_hash, now.isoformat(), expires.isoformat()),
            )
        return f"{intent_id}.{signature}"

    def validate(
        self, *, capability_id: str, owner_token: str, session_nonce: str,
        action_type: str, request_text: str, context_id: str, account_id: str,
        target: dict[str, Any], permission_inventory: dict[str, Any],
        recipients: list[str] | None = None,
    ) -> FirewallDecision:
        if self.global_kill_switch:
            return FirewallDecision(False, "global-kill", "global external-action kill switch is active")
        try:
            intent_id, supplied_signature = owner_token.rsplit(".", 1)
        except ValueError:
            return FirewallDecision(False, "intent-token", "invalid owner intent token")
        intent = self.store.connection.execute(
            "SELECT * FROM owner_intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        if not intent or intent["consumed_at"]:
            return FirewallDecision(False, "intent-replay", "owner intent is absent or already consumed")
        if datetime.fromisoformat(intent["expires_at"]) <= datetime.now(UTC):
            return FirewallDecision(False, "intent-expired", "owner intent expired")
        request_hash = sha256(request_text.encode("utf-8")).hexdigest()
        payload = f"{intent_id}:{session_nonce}:{action_type}:{request_hash}:{intent['expires_at']}"
        expected = hmac.new(self.signing_secret, payload.encode(), sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied_signature):
            return FirewallDecision(False, "intent-signature", "owner intent signature mismatch")
        if (intent["session_nonce"], intent["action_type"], intent["request_hash"]) != (
            session_nonce, action_type, request_hash,
        ):
            return FirewallDecision(False, "intent-binding", "owner intent does not match the request")
        capability = self.store.connection.execute(
            "SELECT * FROM action_capabilities WHERE capability_id=?", (capability_id,)
        ).fetchone()
        if not capability or not capability["enabled"] or capability["kill_switch"]:
            return FirewallDecision(False, "capability-disabled", "capability is disabled or killed")
        if (capability["context_id"], capability["account_id"]) != (context_id, account_id):
            return FirewallDecision(False, "account-context", "account or context mismatch")
        if capability["permission_hash"] != stable_hash(permission_inventory):
            return FirewallDecision(False, "permission-drift", "permission inventory changed")
        if json.loads(capability["target_lock_json"]) != target:
            return FirewallDecision(False, "target-lock", "target differs from the registered destination")
        if recipients and (len(recipients) != 1 or any("," in item or ";" in item for item in recipients)):
            return FirewallDecision(False, "bulk-rejected", "bulk or distribution recipients are rejected")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE owner_intents SET consumed_at=? WHERE intent_id=?", (utc_now(), intent_id)
            )
        return FirewallDecision(True, "allowed", "exact owner-bound capability request validated")

    def set_capability_kill_switch(self, capability_id: str, active: bool) -> None:
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE action_capabilities SET kill_switch=?,updated_at=? WHERE capability_id=?",
                (int(active), utc_now(), capability_id),
            )
