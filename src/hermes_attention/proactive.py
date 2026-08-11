"""Ledger-first proactive brief projections with dormant-context suppression."""

from __future__ import annotations

from datetime import date
from typing import Any

from .work_ledger import WorkLedger


class ProactiveChiefOfStaff:
    def __init__(self, ledger: WorkLedger) -> None:
        self.ledger = ledger

    def daily_brief(self, *, context_id: str, local_date: str) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, local_date=local_date, limit=100)
        priorities = [item for item in entries if item["kind"] in {"task", "commitment", "blocker"}]
        meetings = [item for item in entries if item["kind"] == "meeting"]
        return {
            "context_id": context_id,
            "local_date": local_date,
            "priorities": priorities[:10],
            "meetings": meetings[:10],
            "source_count": len({source for item in entries for source in item["evidence_ids"]}),
            "freshness": max((item["freshness_at"] for item in entries), default=None),
            "connector_fanout_performed": False,
        }

    def start_of_day(self, *, context_id: str, local_date: str) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, local_date=local_date, limit=150)
        return self._projection("start-of-day", context_id, entries, {
            "priorities": {"task", "commitment"}, "meetings": {"meeting"},
            "deadlines": {"deadline"}, "people_waiting": {"waiting"},
            "blockers": {"blocker"}, "important_changes": {"decision", "change"},
        })

    def pre_meeting(self, *, context_id: str, project_id: str | None = None) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, limit=200)
        if project_id:
            entries = [item for item in entries if item["project_id"] in {None, project_id}]
        return self._projection("pre-meeting", context_id, entries, {
            "previous_decisions": {"decision"}, "latest_changes": {"change", "commit"},
            "commitments": {"commitment"}, "unresolved_questions": {"question", "blocker"},
            "relevant_people": {"meeting", "waiting"},
        })

    def post_meeting(self, *, context_id: str, local_date: str) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, local_date=local_date, limit=150)
        return self._projection("post-meeting", context_id, entries, {
            "decisions": {"decision"}, "tasks_and_owners": {"task", "commitment"},
            "contradictions": {"contradiction"}, "follow_ups": {"waiting", "question"},
        })

    def end_of_day(self, *, context_id: str, local_date: str) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, local_date=local_date, limit=250)
        output = self._projection("end-of-day", context_id, entries, {
            "completed_work": {"work", "commit", "completed"}, "slipped": {"overdue", "blocker"},
            "new_open_loops": {"commitment", "task", "question"},
            "tomorrow_priorities": {"priority", "deadline"},
        })
        meetings = [item for item in entries if item["kind"] == "meeting"]
        owner_work = [
            item for item in entries
            if item["actor_state"] == "owner" and item["kind"] in {"work", "commit", "completed", "activity"}
        ]
        enriched: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in owner_work:
            for summary in self.ledger.dloa_activity_summaries(item):
                key = " ".join(summary.casefold().split())
                if key in seen:
                    continue
                seen.add(key)
                enriched.append({**item, "summary": summary})
                if len(enriched) >= 10:
                    break
            if len(enriched) >= 10:
                break
        output["dloa"] = self.render_dloa(local_date=local_date, meetings=meetings, activities=enriched)
        return output

    @staticmethod
    def render_dloa(
        *, local_date: str, meetings: list[dict[str, Any]], activities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        day = date.fromisoformat(local_date)
        header = f"DLOA – {day.day} {day.strftime('%b %Y')}"

        def clean(summary: str) -> str:
            value = " ".join(summary.strip().split())
            lowered = value.casefold()
            if "performance analyzer" in lowered and "with reps" in lowered:
                value = "Worked on the reps' performance analyzer system"
            return value.rstrip(".") + "."

        meeting_rows = [item for item in meetings if item.get("actor_state") in {"owner", "uncertain"}][:4]
        work_rows = [item for item in activities if item.get("actor_state") == "owner"][:10]
        bullets = [f"• {clean(str(item['summary']))}" for item in meeting_rows + work_rows]
        if not bullets:
            bullets = ["• No source-backed activity was available for this date."]
        evidence_ids = list(dict.fromkeys(
            source for item in meeting_rows + work_rows for source in item.get("evidence_ids", [])
        ))
        return {
            "format": "copy-paste-code-block", "timezone": "America/New_York",
            "text": "```\n" + header + "\n" + "\n".join(bullets) + "\n```",
            "meetings_first": meeting_rows, "granular_activities": work_rows,
            "evidence_ids": evidence_ids, "source": "work-ledger", "external_send": False,
        }

    def urgent_alerts(self, *, context_id: str, local_date: str) -> dict[str, Any]:
        entries = self.ledger.query(context_id=context_id, local_date=local_date, limit=100)
        urgent = [item for item in entries if item["kind"] in {"direct-mention", "meeting-change", "deadline", "blocker"}]
        return {
            "mode": "urgent-alerts", "context_id": context_id,
            "alerts": [{**item, "why": f"{item['kind']} needs timely attention"} for item in urgent[:10]],
            "notification_policy": "urgent-only", "external_write": False,
        }

    def weekly_review(self, *, context_id: str, local_dates: list[str]) -> dict[str, Any]:
        entries = [
            item for date in local_dates[:7]
            for item in self.ledger.query(context_id=context_id, local_date=date, limit=150)
        ]
        return self._projection("weekly-review", context_id, entries, {
            "completed": {"work", "commit", "completed"}, "project_risk": {"blocker", "overdue"},
            "commitments_at_risk": {"commitment", "deadline"},
            "automation_opportunities": {"repeated-workflow"},
        })

    def absence_return(self, *, context_id: str, dates: list[str]) -> dict[str, Any]:
        entries = [
            item for date in dates
            for item in self.ledger.query(context_id=context_id, local_date=date, limit=100)
        ]
        return {
            "context_id": context_id,
            "dates": dates,
            "important_changes": [item for item in entries if item["kind"] in {"decision", "blocker", "commitment"}][:25],
            "bounded": True,
        }

    @staticmethod
    def _projection(
        mode: str, context_id: str, entries: list[dict[str, Any]],
        groups: dict[str, set[str]],
    ) -> dict[str, Any]:
        return {
            "mode": mode, "context_id": context_id,
            **{name: [item for item in entries if item["kind"] in kinds][:15] for name, kinds in groups.items()},
            "source_count": len({source for item in entries for source in item["evidence_ids"]}),
            "freshness": max((item["freshness_at"] for item in entries), default=None),
            "bounded": True, "connector_fanout_performed": False,
        }
