"""Transactional SQLite/FTS evidence and operational-state store."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .domain import ActionProposal, EvidenceItem, TaskRecord, utc_now


SCHEMA_VERSION = 4


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
        self.connection.execute("PRAGMA busy_timeout = 5000")
        try:
            self.connection.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            # Some bundled SQLite builds/filesystems cannot safely use WAL.
            self.connection.execute("PRAGMA journal_mode = DELETE")
        self.migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def migrate(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        version_row = self.connection.execute(
            "SELECT value FROM schema_meta WHERE key='version'"
        ).fetchone()
        previous_version = int(version_row["value"]) if version_row else 0
        if previous_version > SCHEMA_VERSION:
            raise RuntimeError("database schema is newer than this application")
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
                CREATE TABLE IF NOT EXISTS ledger_entries (
                    entry_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    local_date TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    actor_id TEXT,
                    actor_state TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence_state TEXT NOT NULL,
                    freshness_at TEXT NOT NULL,
                    project_id TEXT,
                    task_id TEXT,
                    fingerprint TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ledger_context_date_idx
                    ON ledger_entries(context_id, local_date, occurred_at_utc);
                CREATE TABLE IF NOT EXISTS ledger_sources (
                    entry_id TEXT NOT NULL REFERENCES ledger_entries(entry_id) ON DELETE CASCADE,
                    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
                    role TEXT NOT NULL,
                    claim_hash TEXT NOT NULL,
                    PRIMARY KEY(entry_id, evidence_id, role)
                );
                CREATE TABLE IF NOT EXISTS collection_runs (
                    run_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    cursor_before TEXT,
                    cursor_after TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    result TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    error_class TEXT
                );
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    completion_contract TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    lifecycle TEXT NOT NULL CHECK(lifecycle IN ('active','dormant','archived')),
                    freshness_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(project_id),
                    state_json TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    project_id TEXT REFERENCES projects(project_id),
                    decision TEXT NOT NULL,
                    alternatives_json TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    expected_outcome TEXT,
                    actual_outcome TEXT,
                    evidence_ids_json TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    review_at TEXT
                );
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    completion_contract TEXT NOT NULL,
                    state TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    blockers_json TEXT NOT NULL,
                    next_actions_json TEXT NOT NULL,
                    review_cadence TEXT,
                    lifecycle TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS radars (
                    radar_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    cadence TEXT NOT NULL,
                    material_change_json TEXT NOT NULL,
                    notification_policy TEXT NOT NULL,
                    lifecycle TEXT NOT NULL,
                    last_fingerprint TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS radar_runs (
                    run_id TEXT PRIMARY KEY,
                    radar_id TEXT NOT NULL REFERENCES radars(radar_id),
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    result TEXT NOT NULL,
                    fingerprint TEXT,
                    material_change INTEGER NOT NULL DEFAULT 0,
                    evidence_ids_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS capabilities (
                    capability_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    permission_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS capability_revisions (
                    revision_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
                    revision INTEGER NOT NULL,
                    spec_json TEXT NOT NULL,
                    permission_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(capability_id, revision)
                );
                CREATE TABLE IF NOT EXISTS capability_runs (
                    run_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
                    mode TEXT NOT NULL CHECK(mode IN ('dry','shadow','live')),
                    result TEXT NOT NULL,
                    audit_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS model_decisions (
                    run_id TEXT PRIMARY KEY,
                    selected_route TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    signals_json TEXT NOT NULL,
                    override_route TEXT,
                    escalation_route TEXT,
                    reviewer_route TEXT,
                    latency_ms INTEGER,
                    cost_usd REAL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS action_capabilities (
                    capability_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    browser_profile TEXT,
                    target_lock_json TEXT NOT NULL,
                    autonomy_stage INTEGER NOT NULL,
                    reversible INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    permission_hash TEXT NOT NULL,
                    kill_switch INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS owner_intents (
                    intent_id TEXT PRIMARY KEY,
                    session_nonce TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS action_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL REFERENCES actions(proposal_id),
                    lease_until TEXT NOT NULL,
                    state TEXT NOT NULL,
                    provider_id TEXT,
                    result_hash TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS action_attempts_proposal_idx
                    ON action_attempts(proposal_id);
                CREATE TABLE IF NOT EXISTS external_resources (
                    resource_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    created_by_jarvis INTEGER NOT NULL,
                    etag TEXT,
                    state TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS calendar_style_profiles (
                    profile_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    calendar_id_hash TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    evidence_window_json TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    focus_id TEXT PRIMARY KEY,
                    context_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    stopped_at TEXT,
                    policy_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS observation_events (
                    event_id TEXT PRIMARY KEY,
                    focus_id TEXT NOT NULL REFERENCES focus_sessions(focus_id),
                    occurred_at TEXT NOT NULL,
                    app_id TEXT,
                    window_title_hash TEXT,
                    domain TEXT,
                    browser_profile TEXT,
                    context_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            if previous_version < 3:
                self.connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS behavior_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        target_type TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        useful INTEGER NOT NULL,
                        correction TEXT,
                        evidence_ids_json TEXT NOT NULL,
                        provenance_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS behavior_feedback_target_idx
                        ON behavior_feedback(target_type,target_id,created_at);
                    CREATE TABLE IF NOT EXISTS workflow_occurrences (
                        occurrence_id TEXT PRIMARY KEY,
                        context_id TEXT NOT NULL,
                        signature TEXT NOT NULL,
                        description TEXT NOT NULL,
                        duration_minutes REAL NOT NULL,
                        evidence_ids_json TEXT NOT NULL,
                        fingerprint TEXT NOT NULL UNIQUE,
                        occurred_at TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS workflow_occurrence_signature_idx
                        ON workflow_occurrences(context_id,signature,occurred_at);
                    CREATE TABLE IF NOT EXISTS automation_proposals (
                        proposal_id TEXT PRIMARY KEY,
                        context_id TEXT NOT NULL,
                        signature TEXT NOT NULL,
                        status TEXT NOT NULL,
                        occurrence_count INTEGER NOT NULL,
                        frequency_json TEXT NOT NULL,
                        time_cost_minutes REAL NOT NULL,
                        risk TEXT NOT NULL,
                        benefit TEXT NOT NULL,
                        estimated_time_saved_minutes REAL NOT NULL,
                        false_alerts INTEGER NOT NULL DEFAULT 0,
                        evidence_ids_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(context_id,signature)
                    );
                    CREATE TABLE IF NOT EXISTS navigation_previews (
                        preview_id TEXT PRIMARY KEY,
                        focus_id TEXT NOT NULL REFERENCES focus_sessions(focus_id),
                        action_type TEXT NOT NULL,
                        target_json TEXT NOT NULL,
                        payload_hash TEXT NOT NULL,
                        state TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
            if previous_version < 4:
                # The local Codex App Server is an owner-controlled source: a
                # Codex task proves Syed worked on that task, even when an
                # individual assistant item has no author field. This changes
                # only the derived ledger projection; immutable evidence and
                # provenance remain untouched.
                self.connection.execute(
                    """UPDATE ledger_entries
                       SET actor_id='Syed',actor_state='owner',updated_at=?
                       WHERE entry_id IN (
                           SELECT DISTINCT ls.entry_id
                           FROM ledger_sources ls JOIN evidence e ON e.evidence_id=ls.evidence_id
                           WHERE json_extract(e.provenance_json,'$.source_system')='codex'
                       )""",
                    (utc_now(),),
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
        context_clause = ""
        parameters: list[Any] = [match]
        if context_id:
            context_clause = """AND EXISTS (
                SELECT 1 FROM json_each(e.contexts_json) AS labels
                WHERE json_extract(labels.value, '$.context_id') = ?
            )"""
            parameters.append(context_id)
        parameters.append(max(1, min(limit, 50)))
        rows = self.connection.execute(
            f"""
            SELECT e.*, bm25(evidence_fts) AS rank
            FROM evidence_fts JOIN evidence e USING(evidence_id)
            WHERE evidence_fts MATCH ? AND e.tombstoned_at IS NULL
            {context_clause}
            ORDER BY rank LIMIT ?
            """,
            parameters,
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            contexts = json.loads(row["contexts_json"])
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
        native=self.connection.execute("SELECT COALESCE(SUM(cost_usd),0) FROM model_decisions WHERE substr(created_at,1,7)=? AND json_extract(signals_json,'$.source')='jarvis-front-controller'",(year_month,)).fetchone()[0]
        return float(row["cost"])+float(native)

    def set_checkpoint(self, source_id: str, cursor: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO checkpoints VALUES(?,?,?) ON CONFLICT(source_id) DO UPDATE SET cursor=excluded.cursor,updated_at=excluded.updated_at",
                (source_id, cursor, utc_now()),
            )

    def get_checkpoint(self, source_id: str) -> str | None:
        row = self.connection.execute("SELECT cursor FROM checkpoints WHERE source_id=?", (source_id,)).fetchone()
        return str(row["cursor"]) if row else None
