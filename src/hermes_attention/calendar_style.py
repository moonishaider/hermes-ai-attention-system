"""Bounded, owner-reviewable personal Calendar style inference."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from statistics import median
from typing import Any
from uuid import uuid4

from .domain import stable_hash, utc_now
from .storage import Store


class CalendarStyleProfiler:
    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _duration(event: dict[str, Any]) -> int | None:
        start = event.get("start", {}).get("dateTime")
        end = event.get("end", {}).get("dateTime")
        if not start or not end:
            return None
        try:
            return max(0, round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60))
        except (TypeError, ValueError):
            return None

    def derive(
        self, *, account_id: str, calendar_id: str, events: list[dict[str, Any]],
        window_start: str, window_end: str,
    ) -> dict[str, Any]:
        bounded = events[:500]
        if len(bounded) < 5:
            raise ValueError("at least five bounded calendar events are required")
        durations = [value for event in bounded if (value := self._duration(event)) is not None]
        colors = Counter(str(event.get("colorId")) for event in bounded if event.get("colorId"))
        reminders = Counter(json.dumps(event.get("reminders", {}), sort_keys=True) for event in bounded)
        all_day = sum(bool(event.get("start", {}).get("date")) for event in bounded)
        recurring = sum(bool(event.get("recurringEventId") or event.get("recurrence")) for event in bounded)
        with_locations = sum(bool(event.get("location")) for event in bounded)
        with_links = sum(bool(event.get("hangoutLink") or event.get("conferenceData")) for event in bounded)
        titles = [str(event.get("summary") or "") for event in bounded if event.get("summary")]
        profile = {
            "sample_size": len(bounded),
            "median_timed_duration_minutes": median(durations) if durations else None,
            "all_day_ratio": round(all_day / len(bounded), 3),
            "recurrence_ratio": round(recurring / len(bounded), 3),
            "location_ratio": round(with_locations / len(bounded), 3),
            "meeting_link_ratio": round(with_links / len(bounded), 3),
            "common_color_ids": colors.most_common(5),
            "common_reminder_configs": reminders.most_common(3),
            "title_capitalization": "mostly-title-case" if titles and sum(title.istitle() for title in titles) >= len(titles) / 2 else "mixed",
            "timezone_behavior": "preserve-explicit-event-timezone",
            "conflict_and_buffer_preferences": "owner-review-required",
        }
        now = utc_now()
        existing = self.store.connection.execute(
            "SELECT profile_id FROM calendar_style_profiles WHERE account_id=? AND calendar_id_hash=?",
            (account_id, stable_hash(calendar_id)),
        ).fetchone()
        profile_id = str(existing["profile_id"]) if existing else str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO calendar_style_profiles VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(profile_id) DO UPDATE SET profile_json=excluded.profile_json,
                   evidence_window_json=excluded.evidence_window_json,review_status=excluded.review_status,
                   updated_at=excluded.updated_at""",
                (profile_id, account_id, stable_hash(calendar_id), json.dumps(profile, sort_keys=True),
                 json.dumps({"start": window_start, "end": window_end, "sample_size": len(bounded)}, sort_keys=True),
                 "pending-owner-review", now),
            )
        return {"profile_id": profile_id, "profile": profile, "review_status": "pending-owner-review"}

    def review(self, profile_id: str, *, corrections: dict[str, Any]) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT profile_json FROM calendar_style_profiles WHERE profile_id=?", (profile_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown calendar style profile")
        profile = json.loads(row["profile_json"])
        profile.update(corrections)
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE calendar_style_profiles SET profile_json=?,review_status='owner-reviewed',updated_at=? WHERE profile_id=?",
                (json.dumps(profile, sort_keys=True), utc_now(), profile_id),
            )
        return {"profile_id": profile_id, "profile": profile, "review_status": "owner-reviewed"}
