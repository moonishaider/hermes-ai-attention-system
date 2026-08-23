"""Policy-only Computer Awareness sessions; no generic computer-control implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from .domain import stable_hash, utc_now
from .storage import Store


SENSITIVE_APPS = {"com.apple.keychainaccess", "com.1password.1password", "com.apple.systempreferences"}
SENSITIVE_DOMAINS = {"my.1password.com", "icloud.com/keychain", "accounts.google.com/signin"}


@dataclass(frozen=True, slots=True)
class AwarenessPolicy:
    allowed_apps: tuple[str, ...] = ()
    denied_apps: tuple[str, ...] = ()
    allowed_domains: tuple[str, ...] = ()
    denied_domains: tuple[str, ...] = ()


class ComputerAwareness:
    def __init__(self, store: Store) -> None:
        self.store = store

    def start_focus(self, *, context_id: str, minutes: int, policy: AwarenessPolicy) -> str:
        if minutes not in {30, 60, 90, 120}:
            raise ValueError("focus duration must be 30, 60, 90, or 120 minutes")
        focus_id = str(uuid4())
        now = datetime.now(UTC)
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO focus_sessions VALUES(?,?,?,?,?,?,?)",
                (focus_id, context_id, "focus", now.isoformat(),
                 (now + timedelta(minutes=minutes)).isoformat(), None, stable_hash(asdict(policy))),
            )
        return focus_id

    def observe_metadata(
        self, *, focus_id: str, app_id: str, window_title: str | None,
        domain: str | None, browser_profile: str | None, context_id: str,
        incognito: bool = False,
    ) -> str:
        session = self.store.connection.execute(
            "SELECT * FROM focus_sessions WHERE focus_id=?", (focus_id,)
        ).fetchone()
        if not session or session["mode"] != "focus" or session["stopped_at"] or datetime.fromisoformat(session["expires_at"]) <= datetime.now(UTC):
            raise PermissionError("focus session is not active")
        if incognito or app_id.casefold() in SENSITIVE_APPS or any(
            domain and blocked in domain.casefold() for blocked in SENSITIVE_DOMAINS
        ):
            raise PermissionError("sensitive or private surface is excluded")
        if browser_profile not in {None, "Profile 1", "Profile 2"}:
            raise PermissionError("browser profile identity is not proven")
        event_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO observation_events VALUES(?,?,?,?,?,?,?,?,?)",
                (event_id, focus_id, utc_now(), app_id,
                 sha256((window_title or "").encode()).hexdigest() if window_title else None,
                 domain, browser_profile, context_id, "{}"),
            )
        return event_id

    def stop(self, focus_id: str) -> None:
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE focus_sessions SET stopped_at=? WHERE focus_id=? AND stopped_at IS NULL",
                (utc_now(), focus_id),
            )

    def pause(self, focus_id: str) -> None:
        with self.store.connection:
            result = self.store.connection.execute(
                "UPDATE focus_sessions SET mode='paused' WHERE focus_id=? AND mode='focus' AND stopped_at IS NULL",
                (focus_id,),
            )
        if not result.rowcount:
            raise ValueError("active focus session not found")

    def resume(self, focus_id: str) -> None:
        session = self.store.connection.execute(
            "SELECT expires_at,stopped_at,mode FROM focus_sessions WHERE focus_id=?", (focus_id,)
        ).fetchone()
        if not session or session["stopped_at"] or session["mode"] != "paused":
            raise ValueError("paused focus session not found")
        if datetime.fromisoformat(session["expires_at"]) <= datetime.now(UTC):
            raise PermissionError("focus session expired while paused")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE focus_sessions SET mode='focus' WHERE focus_id=?", (focus_id,)
            )

    def timeline(self, focus_id: str) -> dict[str, Any]:
        session = self.store.connection.execute(
            "SELECT * FROM focus_sessions WHERE focus_id=?", (focus_id,)
        ).fetchone()
        if not session:
            raise ValueError("unknown focus session")
        events = [dict(row) for row in self.store.connection.execute(
            """SELECT occurred_at,app_id,domain,browser_profile,context_id
               FROM observation_events WHERE focus_id=? ORDER BY occurred_at""", (focus_id,),
        )]
        return {
            "focus_id": focus_id, "context_id": session["context_id"], "mode": session["mode"],
            "started_at": session["started_at"], "expires_at": session["expires_at"],
            "stopped_at": session["stopped_at"], "events": events,
            "screenshots_retained": 0, "visible_indicator_required": True,
        }

    def stage_navigation(
        self, *, focus_id: str, action_type: str, target: dict[str, Any],
        payload: dict[str, Any] | None = None, ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        safe = {"open", "switch-tab", "search", "scroll", "expand", "collapse", "read", "copy"}
        preview_required = {"type", "upload", "post", "react", "change-setting", "add-to-cart", "download", "submit", "send", "delete"}
        if action_type not in safe | preview_required:
            raise ValueError("unsupported guided action")
        session = self.store.connection.execute(
            "SELECT mode,stopped_at,expires_at FROM focus_sessions WHERE focus_id=?", (focus_id,)
        ).fetchone()
        if not session or session["mode"] != "focus" or session["stopped_at"] or datetime.fromisoformat(session["expires_at"]) <= datetime.now(UTC):
            raise PermissionError("focus session is not active")
        if action_type in safe:
            return {"mode": "navigation", "action": action_type, "target": target, "mutation": False}
        now = datetime.now(UTC)
        preview_id = str(uuid4())
        payload_hash = stable_hash({"action": action_type, "target": target, "payload": payload or {}})
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO navigation_previews VALUES(?,?,?,?,?,?,?,?)",
                (preview_id, focus_id, action_type, json.dumps(target, sort_keys=True), payload_hash,
                 "preview", (now + timedelta(seconds=max(30, min(ttl_seconds, 900)))).isoformat(), now.isoformat()),
            )
        return {
            "mode": "preview", "preview_id": preview_id, "action": action_type,
            "target": target, "payload_hash": payload_hash, "execution_performed": False,
        }
