"""Evidence-backed repeated-workflow detection and owner outcome tracking."""

from __future__ import annotations

from collections import Counter
import json
from typing import Any
from uuid import uuid4

from .domain import stable_hash, utc_now
from .storage import Store


class AutomationMiner:
    """Propose only after three independently evidenced occurrences."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def observe(
        self, *, context_id: str, signature: str, description: str,
        duration_minutes: float, evidence_ids: tuple[str, ...], occurred_at: str,
    ) -> str:
        if not evidence_ids:
            raise ValueError("workflow occurrences require evidence")
        if not signature.strip() or not description.strip():
            raise ValueError("workflow signature and description are required")
        if duration_minutes <= 0 or duration_minutes > 480:
            raise ValueError("duration must be between 0 and 480 minutes")
        found = self.store.connection.execute(
            f"SELECT evidence_id FROM evidence WHERE evidence_id IN ({','.join('?' for _ in evidence_ids)})",
            evidence_ids,
        ).fetchall()
        if {row["evidence_id"] for row in found} != set(evidence_ids):
            raise ValueError("every workflow occurrence must reference existing evidence")
        fingerprint = stable_hash({
            "context": context_id, "signature": signature, "evidence": sorted(evidence_ids),
            "occurred_at": occurred_at,
        })
        existing = self.store.connection.execute(
            "SELECT occurrence_id FROM workflow_occurrences WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        if existing:
            return str(existing["occurrence_id"])
        occurrence_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO workflow_occurrences VALUES(?,?,?,?,?,?,?,?,?)",
                (occurrence_id, context_id, signature, description[:500], float(duration_minutes),
                 json.dumps(sorted(evidence_ids)), fingerprint, occurred_at, utc_now()),
            )
        return occurrence_id

    def propose(self, *, context_id: str, signature: str, risk: str = "low") -> dict[str, Any] | None:
        rows = self.store.connection.execute(
            """SELECT * FROM workflow_occurrences WHERE context_id=? AND signature=?
               ORDER BY occurred_at""", (context_id, signature),
        ).fetchall()
        if len(rows) < 3:
            return None
        if risk not in {"low", "medium", "high"}:
            raise ValueError("invalid workflow risk")
        evidence_ids = sorted({item for row in rows for item in json.loads(row["evidence_ids_json"])})
        total = sum(float(row["duration_minutes"]) for row in rows)
        average = total / len(rows)
        days = [str(row["occurred_at"])[:10] for row in rows]
        frequency = {"observed_days": dict(Counter(days)), "occurrences": len(rows)}
        benefit = f"Could save about {average:.1f} minutes per occurrence after review"
        now = utc_now()
        existing = self.store.connection.execute(
            "SELECT proposal_id,status,false_alerts,created_at FROM automation_proposals "
            "WHERE context_id=? AND signature=?", (context_id, signature),
        ).fetchone()
        proposal_id = str(existing["proposal_id"]) if existing else str(uuid4())
        status = str(existing["status"]) if existing else "proposed"
        false_alerts = int(existing["false_alerts"]) if existing else 0
        created_at = str(existing["created_at"]) if existing else now
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO automation_proposals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(context_id,signature) DO UPDATE SET
                   occurrence_count=excluded.occurrence_count,frequency_json=excluded.frequency_json,
                   time_cost_minutes=excluded.time_cost_minutes,benefit=excluded.benefit,
                   estimated_time_saved_minutes=excluded.estimated_time_saved_minutes,
                   evidence_ids_json=excluded.evidence_ids_json,updated_at=excluded.updated_at""",
                (proposal_id, context_id, signature, status, len(rows), json.dumps(frequency, sort_keys=True),
                 average, risk, benefit, average * len(rows), false_alerts,
                 json.dumps(evidence_ids), created_at, now),
            )
        return {
            "proposal_id": proposal_id, "status": status, "occurrence_count": len(rows),
            "frequency": frequency, "time_cost_minutes": average, "risk": risk,
            "benefit": benefit, "estimated_time_saved_minutes": average * len(rows),
            "evidence_ids": evidence_ids,
        }

    def record_outcome(self, proposal_id: str, outcome: str) -> None:
        if outcome not in {"accepted", "edited", "rejected", "undone"}:
            raise ValueError("invalid automation outcome")
        row = self.store.connection.execute(
            "SELECT status,false_alerts FROM automation_proposals WHERE proposal_id=?", (proposal_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown automation proposal")
        false_alerts = int(row["false_alerts"]) + int(outcome == "rejected")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE automation_proposals SET status=?,false_alerts=?,updated_at=? WHERE proposal_id=?",
                (outcome, false_alerts, utc_now(), proposal_id),
            )
