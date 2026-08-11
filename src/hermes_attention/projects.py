"""Evidence-backed living projects, missions, decisions, and radars."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from .domain import utc_now
from .storage import Store


class Portfolio:
    def __init__(self, store: Store) -> None:
        self.store = store

    def upsert_project(
        self, *, project_id: str, context_id: str, name: str, objective: str,
        completion_contract: str, phase: str, lifecycle: str = "active",
    ) -> None:
        if lifecycle not in {"active", "dormant", "archived"}:
            raise ValueError("invalid project lifecycle")
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO projects VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET name=excluded.name,objective=excluded.objective,
                   completion_contract=excluded.completion_contract,phase=excluded.phase,
                   lifecycle=excluded.lifecycle,updated_at=excluded.updated_at""",
                (project_id, context_id, name, objective, completion_contract, phase, lifecycle, now, now, now),
            )

    def snapshot(self, project_id: str, state: dict[str, Any], evidence_ids: tuple[str, ...]) -> str:
        if not evidence_ids:
            raise ValueError("project snapshots require evidence")
        snapshot_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO project_snapshots VALUES(?,?,?,?,?)",
                (snapshot_id, project_id, json.dumps(state, sort_keys=True), json.dumps(evidence_ids), utc_now()),
            )
            self.store.connection.execute(
                "UPDATE projects SET freshness_at=?,updated_at=? WHERE project_id=?",
                (utc_now(), utc_now(), project_id),
            )
        return snapshot_id

    def record_decision(
        self, *, context_id: str, decision: str, alternatives: list[str], reasoning: str,
        evidence_ids: tuple[str, ...], project_id: str | None = None,
        expected_outcome: str | None = None, review_at: str | None = None,
    ) -> str:
        if not evidence_ids:
            raise ValueError("decisions require evidence")
        decision_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (decision_id, context_id, project_id, decision, json.dumps(alternatives), reasoning,
                 expected_outcome, None, json.dumps(evidence_ids), utc_now(), review_at),
            )
        return decision_id

    def list_active(self, context_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM projects WHERE lifecycle='active'"
        params: tuple[Any, ...] = ()
        if context_id:
            query += " AND context_id=?"
            params = (context_id,)
        return [dict(row) for row in self.store.connection.execute(query + " ORDER BY updated_at DESC", params)]


class MissionRegistry:
    def __init__(self, store: Store) -> None:
        self.store = store

    def create(
        self, *, context_id: str, goal: str, completion_contract: str,
        review_cadence: str | None = None,
    ) -> str:
        mission_id = str(uuid4())
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO missions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (mission_id, context_id, goal, completion_contract, "planned", "[]", "[]", "[]",
                 review_cadence, "active", now, now),
            )
        return mission_id


class RadarRegistry:
    def __init__(self, store: Store) -> None:
        self.store = store

    def create(
        self, *, context_id: str, question: str, sources: list[str], cadence: str,
        material_change: dict[str, Any], notification_policy: str = "digest",
    ) -> str:
        if notification_policy not in {"digest", "urgent-only", "silent"}:
            raise ValueError("invalid notification policy")
        radar_id = str(uuid4())
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO radars VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (radar_id, context_id, question, json.dumps(sources), cadence,
                 json.dumps(material_change, sort_keys=True), notification_policy,
                 "active", None, now, now),
            )
        return radar_id

    def record_run(self, radar_id: str, fingerprint: str, evidence_ids: tuple[str, ...]) -> bool:
        row = self.store.connection.execute(
            "SELECT last_fingerprint FROM radars WHERE radar_id=?", (radar_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown radar")
        changed = bool(row["last_fingerprint"] and row["last_fingerprint"] != fingerprint)
        run_id = str(uuid4())
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO radar_runs VALUES(?,?,?,?,?,?,?,?)",
                (run_id, radar_id, now, now, "success", fingerprint, int(changed), json.dumps(evidence_ids)),
            )
            self.store.connection.execute(
                "UPDATE radars SET last_fingerprint=?,updated_at=? WHERE radar_id=?",
                (fingerprint, now, radar_id),
            )
        return changed
