"""Owner-reviewed context calibration with private, bounded review packets."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .domain import ContextLabel, utc_now
from .security import detect_prompt_injection, redact_secrets
from .storage import Store


CALIBRATION_SOURCES = ("chatgpt_export", "codex")


def _review_hash(evidence_id: str, content_hash: str) -> str:
    return sha256(f"{evidence_id}\0{content_hash}".encode()).hexdigest()


def prepare_context_calibration(
    store: Store,
    *,
    per_source: int = 6,
    allowed_contexts: tuple[str, ...] = ("inside-success", "mitchell", "personal", "mixed", "unknown"),
) -> dict[str, Any]:
    bounded = max(1, min(per_source, 10))
    items: list[dict[str, Any]] = []
    for source_system in CALIBRATION_SOURCES:
        rows = store.connection.execute(
            """
            SELECT evidence_id,title,content,content_hash,provenance_json,contexts_json,confidence_state
            FROM evidence
            WHERE tombstoned_at IS NULL
              AND json_extract(provenance_json,'$.source_system')=?
              AND EXISTS (SELECT 1 FROM json_each(contexts_json) WHERE json_extract(value,'$.context_id')='unknown')
            ORDER BY json_extract(provenance_json,'$.source_timestamp') DESC, evidence_id
            LIMIT ?
            """,
            (source_system, bounded),
        ).fetchall()
        for row in rows:
            provenance = json.loads(row["provenance_json"])
            title, _ = redact_secrets(str(row["title"]))
            content, redactions = redact_secrets(str(row["content"]))
            excerpt = content[:500]
            items.append({
                "evidence_id": row["evidence_id"],
                "review_hash": _review_hash(row["evidence_id"], row["content_hash"]),
                "source_system": source_system,
                "source_date": provenance.get("source_timestamp"),
                "workspace_hint": provenance.get("workspace"),
                "title": title[:200],
                "excerpt": excerpt,
                "prompt_injection_flagged": detect_prompt_injection(content),
                "redaction_count": redactions,
                "current_context": "unknown",
                "confidence_state": row["confidence_state"],
                "allowed_decisions": list(allowed_contexts),
                "decision": None,
                "decision_note": "",
            })
    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "reviewer": "Syed Moonis Haider",
        "instructions": "Set decision only when the context is semantically clear; retain unknown or choose mixed when ambiguity is genuine.",
        "items": items,
        "raw_unredacted_content_stored": False,
    }


def apply_context_calibration(
    store: Store,
    packet: dict[str, Any],
    *,
    confirmed_by: str,
    allowed_contexts: set[str],
) -> dict[str, Any]:
    if packet.get("schema_version") != 1 or not isinstance(packet.get("items"), list):
        raise ValueError("invalid context calibration packet")
    if confirmed_by != "Syed Moonis Haider":
        raise PermissionError("context calibration requires the configured owner")
    changed = 0
    retained_unknown = 0
    with store.connection:
        for item in packet["items"]:
            if not isinstance(item, dict) or item.get("decision") is None:
                continue
            decision = item.get("decision")
            if decision not in allowed_contexts:
                raise ValueError(f"unsupported context decision for {item.get('evidence_id')}")
            row = store.connection.execute(
                "SELECT content_hash,contexts_json FROM evidence WHERE evidence_id=? AND tombstoned_at IS NULL",
                (item.get("evidence_id"),),
            ).fetchone()
            if row is None or item.get("review_hash") != _review_hash(item.get("evidence_id", ""), row["content_hash"]):
                raise ValueError("calibration evidence changed after review packet creation")
            if decision == "unknown":
                retained_unknown += 1
                continue
            label = ContextLabel(decision, 1.0, "owner-confirmed calibration", "owner-v1", corrected_by_user=True)
            store.connection.execute(
                "UPDATE evidence SET contexts_json=? WHERE evidence_id=?",
                (json.dumps([asdict(label)], sort_keys=True, separators=(",", ":")), item["evidence_id"]),
            )
            changed += 1
    store.audit("Syed Moonis Haider", "context.calibration.apply", None, "success", {
        "changed": changed,
        "retained_unknown": retained_unknown,
        "packet_item_count": len(packet["items"]),
        "raw_content_logged": False,
    })
    return {"changed": changed, "retained_unknown": retained_unknown, "reviewed": len(packet["items"])}
