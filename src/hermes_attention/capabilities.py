"""Declarative Capability Studio with permission intersection and protected fields."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4

from .domain import stable_hash, utc_now
from .storage import Store


PROTECTED_KEYS = {
    "credentials", "oauth_scopes", "security_policy", "model_budget",
    "company_permissions", "client_permissions", "action_destination",
    "protected_code", "hermes_core", "filesystem_root", "browser_control",
}


@dataclass(frozen=True, slots=True)
class CapabilityValidation:
    allowed: bool
    reason: str
    requested_tools: tuple[str, ...]
    granted_tools: tuple[str, ...]
    requires_code: bool = False


class CapabilityStudio:
    KINDS = {"mission", "radar", "schedule", "skill", "report-template", "workflow"}

    def __init__(self, store: Store, approved_tools: set[str]) -> None:
        self.store = store
        self.approved_tools = approved_tools

    @staticmethod
    def _walk_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for nested in value.values() for key in CapabilityStudio._walk_keys(nested)}
        if isinstance(value, list):
            return {key for nested in value for key in CapabilityStudio._walk_keys(nested)}
        return set()

    def validate(self, spec: dict[str, Any]) -> CapabilityValidation:
        kind = str(spec.get("kind", ""))
        if kind not in self.KINDS:
            return CapabilityValidation(False, "unsupported capability kind", (), ())
        protected = sorted(self._walk_keys(spec) & PROTECTED_KEYS)
        if protected:
            return CapabilityValidation(False, f"protected fields requested: {', '.join(protected)}", (), ())
        requested = tuple(sorted({str(tool) for tool in spec.get("tools", [])}))
        granted = tuple(tool for tool in requested if tool in self.approved_tools)
        if granted != requested:
            return CapabilityValidation(False, "requested tools exceed current permissions", requested, granted)
        requires_code = bool(spec.get("requires_code", False))
        return CapabilityValidation(
            True, "declarative specification is within current permissions",
            requested, granted, requires_code=requires_code,
        )

    def create(self, spec: dict[str, Any], *, permission_inventory: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate(spec)
        if not validation.allowed:
            raise ValueError(validation.reason)
        if validation.requires_code:
            return {
                "status": "codex-spec-only",
                "implementation_spec": spec,
                "activation_performed": False,
            }
        capability_id = str(uuid4())
        now = utc_now()
        permission_hash = stable_hash(permission_inventory)
        spec_json = json.dumps(spec, sort_keys=True, separators=(",", ":"))
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO capabilities VALUES(?,?,?,?,?,?,?,?)",
                (capability_id, spec["kind"], spec["context_id"], "draft", spec_json,
                 permission_hash, now, now),
            )
            self.store.connection.execute(
                "INSERT INTO capability_revisions VALUES(?,?,?,?,?,?)",
                (str(uuid4()), capability_id, 1, spec_json, permission_hash, now),
            )
        return {"capability_id": capability_id, "status": "draft", "validation": validation}

    def dry_run(self, capability_id: str, *, current_permission_inventory: dict[str, Any]) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT * FROM capabilities WHERE capability_id=?", (capability_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown capability")
        if row["permission_hash"] != stable_hash(current_permission_inventory):
            raise PermissionError("permission inventory changed; re-review required")
        run_id = str(uuid4())
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO capability_runs VALUES(?,?,?,?,?,?,?)",
                (run_id, capability_id, "dry", "validated", "{}", now, now),
            )
        return {"run_id": run_id, "mode": "dry", "external_write": False}

    def set_status(self, capability_id: str, status: str) -> None:
        if status not in {"draft", "shadow", "active", "disabled", "archived"}:
            raise ValueError("invalid capability status")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE capabilities SET status=?,updated_at=? WHERE capability_id=?",
                (status, utc_now(), capability_id),
            )

    def record_feedback(
        self, *, capability_id: str, useful: bool, correction: str | None,
        evidence_ids: tuple[str, ...], provenance: dict[str, Any],
    ) -> str:
        row = self.store.connection.execute(
            "SELECT status FROM capabilities WHERE capability_id=?", (capability_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown capability")
        if correction and len(correction) > 1_000:
            raise ValueError("feedback correction is too large")
        feedback_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO behavior_feedback VALUES(?,?,?,?,?,?,?,?)",
                (feedback_id, "capability", capability_id, int(useful), correction,
                 json.dumps(sorted(evidence_ids)), json.dumps(provenance, sort_keys=True), utc_now()),
            )
            if not useful and row["status"] in {"active", "shadow"}:
                self.store.connection.execute(
                    "UPDATE capabilities SET status='disabled',updated_at=? WHERE capability_id=?",
                    (utc_now(), capability_id),
                )
        return feedback_id
