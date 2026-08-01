"""Attention ranking, context handoffs, commitments, and contradictions."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .storage import Store


class AttentionEngine:
    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _score(task: dict[str, Any]) -> float:
        score = float(task["priority"])
        if task["status"] == "blocked":
            score += 15
        if task["due_at"]:
            try:
                due = datetime.fromisoformat(task["due_at"])
                hours = (due - datetime.now(UTC)).total_seconds() / 3600
                if hours <= 0:
                    score += 50
                elif hours <= 24:
                    score += 35
                elif hours <= 72:
                    score += 20
            except ValueError:
                score += 5
        score += task["confidence"] * 10
        return score

    def queue(self, *, context_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        tasks = self.store.list_tasks(context_id=context_id)
        ranked = [{**task, "score": self._score(task), "evidence_ids": json.loads(task["evidence_ids_json"])} for task in tasks]
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[: max(1, min(limit, 25))]

    def context_handoff(self, context_id: str) -> dict[str, Any]:
        queue = self.queue(context_id=context_id, limit=5)
        blocked = [item for item in queue if item["status"] == "blocked"]
        return {
            "context": context_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": f"{len(queue)} active attention items; {len(blocked)} blocked.",
            "next_actions": queue[:3],
            "blocked": blocked,
            "uncertainty": [item for item in queue if item["status"] == "triage"],
        }

    def project_resume(self, project_query: str, *, context_id: str | None = None) -> dict[str, Any]:
        evidence = self.store.search_evidence(project_query, context_id=context_id, limit=8)
        return {
            "query": project_query,
            "context": context_id or "cross-context-private",
            "evidence": evidence,
            "next_actions": self.queue(context_id=context_id, limit=3),
            "status": "supported" if evidence else "insufficient-evidence",
        }
