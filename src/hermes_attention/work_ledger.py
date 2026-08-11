"""Incremental, provenance-linked work ledger used by every Jarvis projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from .domain import stable_hash, utc_now
from .domain import TaskRecord
from .storage import Store


CONTEXT_TIMEZONES = {
    "inside-success": "America/New_York",
    "mitchell": "America/New_York",
    "personal": "Asia/Karachi",
}


@dataclass(frozen=True, slots=True)
class LedgerEntryInput:
    kind: str
    occurred_at_utc: str
    context_id: str
    summary: str
    evidence_ids: tuple[str, ...]
    actor_id: str | None = None
    actor_state: str = "uncertain"
    confidence_state: str = "inferred"
    project_id: str | None = None
    task_id: str | None = None


class WorkLedger:
    """Single SQLite-backed activity record; source provenance remains immutable evidence."""

    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _clock(context_id: str) -> str:
        if context_id in {"mixed", "unknown"}:
            raise ValueError("mixed/unknown ledger entries require explicit timezone")
        return CONTEXT_TIMEZONES.get(context_id, "UTC")

    def record(self, value: LedgerEntryInput, *, timezone: str | None = None) -> tuple[str, bool]:
        if not value.evidence_ids:
            raise ValueError("ledger entries require source evidence")
        clock = timezone or self._clock(value.context_id)
        occurred = datetime.fromisoformat(value.occurred_at_utc.replace("Z", "+00:00"))
        if occurred.tzinfo is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        occurred = occurred.astimezone(UTC)
        local_date = occurred.astimezone(ZoneInfo(clock)).date().isoformat()
        evidence_rows = {
            row["evidence_id"]: row
            for row in self.store.connection.execute(
                f"SELECT evidence_id,content_hash FROM evidence WHERE evidence_id IN ({','.join('?' for _ in value.evidence_ids)})",
                value.evidence_ids,
            ).fetchall()
        }
        if set(evidence_rows) != set(value.evidence_ids):
            raise ValueError("every ledger source must reference existing evidence")
        fingerprint = stable_hash({
            "kind": value.kind,
            "occurred_at": occurred.isoformat(),
            "context": value.context_id,
            "summary": value.summary,
            "actor": value.actor_id,
            "evidence": sorted(value.evidence_ids),
        })
        existing = self.store.connection.execute(
            "SELECT entry_id FROM ledger_entries WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        if existing:
            return str(existing["entry_id"]), False
        entry_id = str(uuid4())
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    entry_id, value.kind, occurred.isoformat(), clock, local_date,
                    value.context_id, value.actor_id, value.actor_state, value.summary,
                    value.confidence_state, now, value.project_id, value.task_id,
                    fingerprint, now, now,
                ),
            )
            for evidence_id in value.evidence_ids:
                claim_hash = sha256(
                    f"{evidence_rows[evidence_id]['content_hash']}:{value.summary}".encode("utf-8")
                ).hexdigest()
                self.store.connection.execute(
                    "INSERT INTO ledger_sources VALUES(?,?,?,?)",
                    (entry_id, evidence_id, "supports", claim_hash),
                )
        return entry_id, True

    def query(
        self, *, context_id: str, local_date: str | None = None,
        include_dormant: bool = False, limit: int = 100,
    ) -> list[dict[str, Any]]:
        if context_id == "mitchell" and not include_dormant:
            return []
        parameters: list[Any] = [context_id]
        where = "context_id=?"
        if local_date:
            where += " AND local_date=?"
            parameters.append(local_date)
        parameters.append(max(1, min(limit, 500)))
        rows = self.store.connection.execute(
            f"SELECT * FROM ledger_entries WHERE {where} ORDER BY occurred_at_utc DESC LIMIT ?",
            parameters,
        ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["evidence_ids"] = [
                source["evidence_id"] for source in self.store.connection.execute(
                    "SELECT evidence_id FROM ledger_sources WHERE entry_id=? ORDER BY evidence_id",
                    (row["entry_id"],),
                ).fetchall()
            ]
            output.append(item)
        return output

    def dloa_activity_summary(self, item: dict[str, Any]) -> str:
        """Derive a short activity statement without copying raw evidence.

        Historical Codex projection rows deliberately stored the evidence title,
        which can end in a role label such as ``— assistant``.  That label is
        provenance, not useful work.  The DLOA projection may inspect the same
        local immutable evidence and select one bounded action sentence, while
        keeping the ledger and source content unchanged.
        """
        return self.dloa_activity_summaries(item)[0]

    def dloa_activity_summaries(self, item: dict[str, Any]) -> list[str]:
        """Return at most three distinct, bounded statements for one source."""
        evidence_ids = tuple(str(value) for value in item.get("evidence_ids", ()))[:3]
        if not evidence_ids:
            return [self._fallback_activity(str(item.get("summary") or ""))]
        rows = self.store.connection.execute(
            f"""SELECT title,content,provenance_json FROM evidence
                WHERE evidence_id IN ({','.join('?' for _ in evidence_ids)})
                  AND tombstoned_at IS NULL ORDER BY indexed_at DESC""",
            evidence_ids,
        ).fetchall()
        for row in rows:
            provenance = json.loads(row["provenance_json"])
            title = str(row["title"] or "")
            content = str(row["content"] or "")
            source = str(provenance.get("source_system") or "")
            if source == "codex":
                candidates = self._codex_activities(title, content)
                if candidates:
                    return candidates
        return [self._fallback_activity(str(item.get("summary") or ""))]

    @staticmethod
    def _codex_activities(title: str, content: str) -> list[str]:
        base = title.rsplit(" — ", 1)[0].strip()
        lowered = f"{base} {content[:4_000]}".casefold()
        candidates: list[str] = []
        if "magic mike" in base.casefold():
            candidates.append("Worked on the reps' performance analyzer system")
        action_verbs = (
            "implemented", "fixed", "updated", "added", "built", "verified",
            "completed", "configured", "created", "reviewed", "investigated",
            "migrated", "connected", "tested", "documented", "refined", "reworked",
            "hardened", "expanded", "removed", "corrected", "refactored", "integrated",
            "deployed", "validated", "ran",
        )
        for raw_line in content.splitlines()[:80]:
            line = re.sub(r"^[\s#>*`\-\d.)]+", "", raw_line).strip()
            line = re.sub(r"[`*_]", "", line)
            line = re.sub(r"https?://\S+", "", line)
            line = " ".join(line.split())
            if not 12 <= len(line) <= 220:
                continue
            lowered_line = line.casefold()
            first_word = lowered_line.split(" ", 1)[0].rstrip(":")
            if first_word in action_verbs:
                if "performance analyzer" in lowered_line:
                    sentence = "Worked on the reps' performance analyzer system"
                else:
                    sentence = re.split(r"(?<=[.!?])\s+", line, maxsplit=1)[0].rstrip(". ")
                if sentence.casefold() not in {value.casefold() for value in candidates}:
                    candidates.append(sentence)
                if len(candidates) >= 3:
                    break
        if not candidates and "performance analyzer" in lowered:
            candidates.append("Worked on the reps' performance analyzer system")
        if not candidates:
            candidates.append(WorkLedger._fallback_activity(base))
        return candidates[:3]

    @staticmethod
    def _fallback_activity(summary: str) -> str:
        value = summary.rsplit(" — ", 1)[0].strip()
        value = " ".join(value.split())[:180]
        if not value or value.casefold() in {"user", "assistant", "agent"}:
            return "Reviewed source-backed project work"
        if value.casefold().startswith(("worked ", "implemented ", "fixed ", "updated ", "reviewed ")):
            return value.rstrip(".")
        return f"Worked on {value}".rstrip(".")

    def open_commitment(
        self, *, title: str, context_id: str, evidence_ids: tuple[str, ...],
        owner: str = "Syed", due_at: str | None = None,
    ) -> str:
        if not evidence_ids:
            raise ValueError("commitments require evidence")
        task_id = stable_hash({"context": context_id, "title": title, "evidence": sorted(evidence_ids)})[:32]
        task = TaskRecord(
            task_id=task_id, title=title, context_id=context_id, task_type="commitment",
            status="open", priority=50, owner=owner, waiting_on=None, due_at=due_at,
            evidence_ids=evidence_ids, confidence=1.0,
        )
        self.store.upsert_task(task)
        return task_id

    def verify_commitment_complete(self, task_id: str, *, evidence_id: str) -> None:
        task = self.store.connection.execute(
            "SELECT * FROM tasks WHERE task_id=? AND task_type='commitment'", (task_id,)
        ).fetchone()
        evidence = self.store.connection.execute(
            "SELECT evidence_id,contexts_json FROM evidence WHERE evidence_id=? AND tombstoned_at IS NULL",
            (evidence_id,),
        ).fetchone()
        if not task or not evidence:
            raise ValueError("commitment or completion evidence not found")
        contexts = {str(item.get("context_id")) for item in json.loads(evidence["contexts_json"])}
        if str(task["context_id"]) not in contexts:
            raise PermissionError("completion evidence belongs to another context")
        evidence_ids = sorted(set(json.loads(task["evidence_ids_json"])) | {evidence_id})
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE tasks SET status='completed',evidence_ids_json=?,confidence=1.0,updated_at=? WHERE task_id=?",
                (json.dumps(evidence_ids), utc_now(), task_id),
            )

    def start_collection(self, source_id: str) -> str:
        run_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO collection_runs(run_id,source_id,cursor_before,started_at,result) VALUES(?,?,?,?,?)",
                (run_id, source_id, self.store.get_checkpoint(source_id), utc_now(), "running"),
            )
        return run_id

    def finish_collection(
        self, run_id: str, *, cursor_after: str | None, item_count: int,
        result: str = "success", error_class: str | None = None,
    ) -> None:
        row = self.store.connection.execute(
            "SELECT source_id FROM collection_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown collection run")
        with self.store.connection:
            self.store.connection.execute(
                """UPDATE collection_runs SET cursor_after=?,finished_at=?,result=?,item_count=?,error_class=?
                   WHERE run_id=?""",
                (cursor_after, utc_now(), result, max(0, item_count), error_class, run_id),
            )
        if result == "success" and cursor_after is not None:
            self.store.set_checkpoint(str(row["source_id"]), cursor_after)

    def refresh_from_evidence(self, *, limit: int = 500) -> dict[str, Any]:
        """Incrementally project immutable evidence into the ledger.

        This is a bounded cursor walk, not a connector rescan. Original content
        and provenance stay linked through ``ledger_sources``.
        """
        checkpoint_id = "work-ledger:evidence-v1"
        raw_cursor = self.store.get_checkpoint(checkpoint_id)
        cursor = json.loads(raw_cursor) if raw_cursor else {"indexed_at": "", "evidence_id": ""}
        batch_limit = max(1, min(limit, 2_000))
        rows = self.store.connection.execute(
            """SELECT evidence_id,title,provenance_json,contexts_json,indexed_at
               FROM evidence
               WHERE tombstoned_at IS NULL
                 AND (indexed_at > ? OR (indexed_at = ? AND evidence_id > ?))
               ORDER BY indexed_at,evidence_id LIMIT ?""",
            (
                str(cursor.get("indexed_at", "")), str(cursor.get("indexed_at", "")),
                str(cursor.get("evidence_id", "")), batch_limit,
            ),
        ).fetchall()
        inserted = 0
        skipped = 0
        for row in rows:
            provenance = json.loads(row["provenance_json"])
            labels = json.loads(row["contexts_json"])
            context_id = next(
                (str(label.get("context_id")) for label in labels if label.get("context_id") != "mixed"),
                "unknown",
            )
            if any(label.get("context_id") == "mixed" for label in labels):
                context_id = "mixed"
            occurred_at = provenance.get("source_timestamp") or provenance.get("retrieved_at") or row["indexed_at"]
            author = str(provenance.get("author") or "").strip()
            normalized_author = " ".join(author.lower().split())
            source_system = str(provenance.get("source_system") or "evidence")
            owner = source_system == "codex" or normalized_author in {
                "syed", "sid", "syed moonis haider", "moonis haider",
            }
            kind = {
                "calendar": "meeting", "google_calendar": "meeting", "github": "commit",
                "codex": "work", "chatgpt": "work", "gemini": "work", "zoom": "meeting",
            }.get(source_system, "activity")
            try:
                _, was_inserted = self.record(
                    LedgerEntryInput(
                        kind=kind, occurred_at_utc=str(occurred_at), context_id=context_id,
                        summary=str(row["title"])[:500], evidence_ids=(str(row["evidence_id"]),),
                        actor_id=author or "Syed" if owner else None,
                        actor_state="owner" if owner else "other" if author else "uncertain",
                        confidence_state="inferred",
                    ),
                    timezone="UTC" if context_id in {"mixed", "unknown"} else None,
                )
                inserted += int(was_inserted)
            except (TypeError, ValueError):
                skipped += 1
        if rows:
            last = rows[-1]
            self.store.set_checkpoint(
                checkpoint_id,
                json.dumps({"indexed_at": last["indexed_at"], "evidence_id": last["evidence_id"]}, sort_keys=True),
            )
        return {
            "processed": len(rows), "inserted": inserted, "skipped": skipped,
            "has_more": len(rows) == batch_limit, "checkpoint": checkpoint_id,
        }
