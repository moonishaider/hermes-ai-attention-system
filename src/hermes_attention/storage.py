"""Transactional SQLite/FTS evidence and operational-state store."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .domain import ActionProposal, EvidenceItem, TaskRecord, utc_now


SCHEMA_VERSION = 1


class ProvenanceConflict(RuntimeError):
    pass


class Store:
    def __init__(self, database: Path | str) -> None:
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def migrate(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    provenance_hash TEXT NOT NULL,
                    contexts_json TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    confidence_state TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    tombstoned_at TEXT
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
                    evidence_id UNINDEXED,
                    title,
                    content,
                    tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS memory_proposals (
                    memory_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('proposed','confirmed','superseded','rejected')),
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    owner TEXT NOT NULL,
                    waiting_on TEXT,
                    due_at TEXT,
                    evidence_ids_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS actions (
                    proposal_id TEXT PRIMARY KEY,
                    proposal_json TEXT NOT NULL,
                    preview_hash TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    context_id TEXT,
                    outcome TEXT NOT NULL,
                    correlation_id TEXT,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS usage_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    context_id TEXT,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    success INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    source_id TEXT PRIMARY KEY,
                    cursor TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self.connection.execute(
                "INSERT INTO schema_meta(key,value) VALUES('version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def add_evidence(self, item: EvidenceItem) -> bool:
        provenance_json = self._json(asdict(item.provenance))
        existing = self.connection.execute(
            "SELECT provenance_json, content_hash FROM evidence WHERE evidence_id=?",
            (item.evidence_id,),
        ).fetchone()
        if existing:
            if existing["provenance_json"] != provenance_json:
                raise ProvenanceConflict(f"immutable provenance changed for {item.evidence_id}")
            if existing["content_hash"] == item.content_hash:
                return False
        contexts_json = self._json([asdict(label) for label in item.contexts])
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO evidence(
                    evidence_id,title,content,content_hash,provenance_json,provenance_hash,
                    contexts_json,sensitivity,confidence_state,indexed_at,tombstoned_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,NULL)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    title=excluded.title, content=excluded.content, content_hash=excluded.content_hash,
                    contexts_json=excluded.contexts_json, sensitivity=excluded.sensitivity,
                    confidence_state=excluded.confidence_state, indexed_at=excluded.indexed_at,
                    tombstoned_at=NULL
                """,
                (
                    item.evidence_id,
                    item.title,
                    item.content,
                    item.content_hash,
                    provenance_json,
                    item.provenance.fingerprint,
                    contexts_json,
                    item.sensitivity,
                    item.confidence_state,
                    utc_now(),
                ),
            )
            self.connection.execute("DELETE FROM evidence_fts WHERE evidence_id=?", (item.evidence_id,))
            self.connection.execute(
                "INSERT INTO evidence_fts(evidence_id,title,content) VALUES(?,?,?)",
                (item.evidence_id, item.title, item.content),
            )
        return True

    def search_evidence(self, query: str, *, context_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        terms = [term for term in query.replace('"', " ").split() if term]
        if not terms:
            return []
        match = " AND ".join(f'"{term}"' for term in terms)
        rows = self.connection.execute(
            """
            SELECT e.*, bm25(evidence_fts) AS rank
            FROM evidence_fts JOIN evidence e USING(evidence_id)
            WHERE evidence_fts MATCH ? AND e.tombstoned_at IS NULL
            ORDER BY rank LIMIT ?
            """,
            (match, max(1, min(limit, 50))),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            contexts = json.loads(row["contexts_json"])
            if context_id and not any(label["context_id"] == context_id for label in contexts):
                continue
            results.append(
                {
                    "evidence_id": row["evidence_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "content_hash": row["content_hash"],
                    "provenance": json.loads(row["provenance_json"]),
                    "contexts": contexts,
                    "confidence_state": row["confidence_state"],
                    "rank": row["rank"],
                }
            )
        return results

    def tombstone_evidence(self, evidence_id: str, *, reason: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE evidence SET tombstoned_at=? WHERE evidence_id=?",
                (utc_now(), evidence_id),
            )
            self.audit("system", "evidence.tombstone", "unknown", "success", {"evidence_id": evidence_id, "reason": reason})

    def propose_memory(
        self,
        memory_id: str,
        statement: str,
        namespace: str,
        context_id: str,
        evidence_ids: Iterable[str],
        confidence: float,
    ) -> None:
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        with self.connection:
            self.connection.execute(
                """INSERT INTO memory_proposals
                (memory_id,statement,namespace,context_id,evidence_ids_json,confidence,status,created_at)
                VALUES(?,?,?,?,?,?,'proposed',?)""",
                (memory_id, statement, namespace, context_id, self._json(list(evidence_ids)), confidence, utc_now()),
            )

    def upsert_task(self, task: TaskRecord) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(task_id) DO UPDATE SET
                    title=excluded.title, context_id=excluded.context_id,
                    task_type=excluded.task_type, status=excluded.status,
                    priority=excluded.priority, owner=excluded.owner,
                    waiting_on=excluded.waiting_on, due_at=excluded.due_at,
                    evidence_ids_json=excluded.evidence_ids_json,
                    confidence=excluded.confidence, updated_at=excluded.updated_at
                """,
                (
                    task.task_id,
                    task.title,
                    task.context_id,
                    task.task_type,
                    task.status,
                    task.priority,
                    task.owner,
                    task.waiting_on,
                    task.due_at,
                    self._json(task.evidence_ids),
                    task.confidence,
                    utc_now(),
                ),
            )

    def list_tasks(self, *, context_id: str | None = None, statuses: tuple[str, ...] = ("triage", "open", "blocked")) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in statuses)
        parameters: list[Any] = list(statuses)
        query = f"SELECT * FROM tasks WHERE status IN ({placeholders})"
        if context_id:
            query += " AND context_id=?"
            parameters.append(context_id)
        query += " ORDER BY priority DESC, due_at IS NULL, due_at, updated_at DESC"
        return [dict(row) for row in self.connection.execute(query, parameters).fetchall()]

    def save_action(self, proposal: ActionProposal) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO actions VALUES(?,?,?,?,?,?)",
                (
                    proposal.proposal_id,
                    self._json(asdict(proposal)),
                    proposal.preview_hash,
                    proposal.idempotency_key,
                    proposal.state,
                    utc_now(),
                ),
            )

    def get_action(self, proposal_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM actions WHERE proposal_id=?", (proposal_id,)).fetchone()
        return dict(row) if row else None

    def set_action_state(self, proposal_id: str, state: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE actions SET state=?, updated_at=? WHERE proposal_id=?",
                (state, utc_now(), proposal_id),
            )

    def audit(
        self,
        actor: str,
        operation: str,
        context_id: str | None,
        outcome: str,
        metadata: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO audit_events(occurred_at,actor,operation,context_id,outcome,correlation_id,metadata_json) VALUES(?,?,?,?,?,?,?)",
                (utc_now(), actor, operation, context_id, outcome, correlation_id, self._json(metadata)),
            )

    def record_usage(
        self,
        *,
        provider: str,
        model: str,
        feature: str,
        context_id: str | None,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        success: bool,
    ) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO usage_events VALUES(NULL,?,?,?,?,?,?,?,?,?,?)",
                (utc_now(), provider, model, feature, context_id, input_tokens, output_tokens, cost_usd, latency_ms, int(success)),
            )

    def monthly_cost(self, year_month: str) -> float:
        row = self.connection.execute(
            "SELECT COALESCE(SUM(cost_usd),0) AS cost FROM usage_events WHERE substr(occurred_at,1,7)=?",
            (year_month,),
        ).fetchone()
        return float(row["cost"])

    def set_checkpoint(self, source_id: str, cursor: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO checkpoints VALUES(?,?,?) ON CONFLICT(source_id) DO UPDATE SET cursor=excluded.cursor,updated_at=excluded.updated_at",
                (source_id, cursor, utc_now()),
            )

    def get_checkpoint(self, source_id: str) -> str | None:
        row = self.connection.execute("SELECT cursor FROM checkpoints WHERE source_id=?", (source_id,)).fetchone()
        return str(row["cursor"]) if row else None
