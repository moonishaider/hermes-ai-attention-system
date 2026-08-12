"""Narrow personal Calendar and Gmail-draft request wrappers.

The caller supplies an authenticated transport. This module deliberately has no send-mail,
work-account, generic request, arbitrary-calendar operation, or delete operation beyond
undoing an event that Jarvis itself created and recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from .domain import stable_hash, utc_now
from .storage import Store
from .google_offline_oauth import _ssl_context
from .personal_google_action_oauth import PersonalGoogleActionTokenManager


Transport = Callable[[str, str, dict[str, Any] | None, dict[str, str] | None], dict[str, Any]]


class PersonalGoogleActionTransport:
    """Exact endpoint/method allowlist; notably, Gmail send does not exist."""

    def __init__(self, tokens: PersonalGoogleActionTokenManager | None = None,
                 *, opener: Callable[..., Any] = urlopen) -> None:
        self.tokens, self.opener = tokens or PersonalGoogleActionTokenManager(), opener

    @staticmethod
    def _allowed(method: str, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path
        if parsed.scheme != "https":
            return False
        if parsed.netloc == "www.googleapis.com":
            base = "/calendar/v3/calendars/primary/events"
            return (method == "POST" and path == base) or (
                method in {"PATCH", "DELETE"} and path.startswith(base + "/") and path.count("/") == 6)
        if parsed.netloc == "gmail.googleapis.com":
            base = "/gmail/v1/users/me/drafts"
            return (method == "POST" and path == base) or (
                method in {"GET", "PUT"} and path.startswith(base + "/") and path.count("/") == 6)
        return False

    def __call__(self, method: str, url: str, body: dict[str, Any] | None,
                 params: dict[str, str] | None) -> dict[str, Any]:
        method = method.upper()
        if not self._allowed(method, url):
            raise PermissionError("personal Google endpoint or method is not allowlisted")
        target = url + (("?" + urlencode(params)) if params else "")
        data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
        request = Request(target, data=data, method=method, headers={
            "Authorization": f"Bearer {self.tokens.access_token()}", "Accept": "application/json",
            **({"Content-Type": "application/json"} if data is not None else {}),
        })
        try:
            with self.opener(request, timeout=30, context=_ssl_context()) as response:
                raw = response.read()
        except Exception as exc:
            raise RuntimeError(f"personal Google request failed: {type(exc).__name__}") from exc
        return json.loads(raw.decode()) if raw else {}


@dataclass(frozen=True, slots=True)
class PersonalGoogleResult:
    provider_id: str
    resource_kind: str
    direct_url: str


class PersonalCalendarActions:
    BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(self, store: Store, transport: Transport, *, calendar_id: str, capability_id: str) -> None:
        self.store = store
        self.transport = transport
        self.calendar_id = calendar_id
        self.capability_id = capability_id

    def create_explicit(self, event: dict[str, Any]) -> PersonalGoogleResult:
        forbidden = {"attendees", "recurrence", "conferenceData"} & set(event)
        if forbidden:
            raise PermissionError("attendees, recurrence, and conference creation require preview")
        if not event.get("summary") or not (event.get("start") and event.get("end")):
            raise ValueError("summary, start, and end are required")
        url = f"{self.BASE}/calendars/{quote(self.calendar_id, safe='')}/events"
        payload = self.transport("POST", url, event, {"sendUpdates": "none"})
        provider_id = str(payload["id"])
        self._record(provider_id, payload)
        return PersonalGoogleResult(provider_id, "calendar-event", str(payload.get("htmlLink", "")))

    def update_created(self, provider_id: str, patch: dict[str, Any]) -> PersonalGoogleResult:
        self._assert_owned(provider_id)
        if {"attendees", "recurrence", "conferenceData"} & set(patch):
            raise PermissionError("unsafe event mutation")
        url = f"{self.BASE}/calendars/{quote(self.calendar_id, safe='')}/events/{quote(provider_id, safe='')}"
        payload = self.transport("PATCH", url, patch, {"sendUpdates": "none"})
        self._record(provider_id, payload)
        return PersonalGoogleResult(provider_id, "calendar-event", str(payload.get("htmlLink", "")))

    def undo_created(self, provider_id: str) -> None:
        self._assert_owned(provider_id)
        url = f"{self.BASE}/calendars/{quote(self.calendar_id, safe='')}/events/{quote(provider_id, safe='')}"
        self.transport("DELETE", url, None, {"sendUpdates": "none"})
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE external_resources SET state='undone',updated_at=? WHERE resource_id=?",
                (utc_now(), f"calendar:{provider_id}"),
            )

    def _assert_owned(self, provider_id: str) -> None:
        row = self.store.connection.execute(
            "SELECT created_by_jarvis,state FROM external_resources WHERE resource_id=?",
            (f"calendar:{provider_id}",),
        ).fetchone()
        if not row or not row["created_by_jarvis"] or row["state"] != "active":
            raise PermissionError("event was not created by Jarvis")

    def _record(self, provider_id: str, payload: dict[str, Any]) -> None:
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                """INSERT INTO external_resources VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(resource_id) DO UPDATE SET etag=excluded.etag,
                   metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (f"calendar:{provider_id}", self.capability_id, provider_id, 1,
                 payload.get("etag"), "active", json.dumps({
                     "calendar_id_hash": stable_hash(self.calendar_id),
                     "summary": str(payload.get("summary") or "")[:200],
                     "start": payload.get("start", {}), "end": payload.get("end", {}),
                     "colorId": payload.get("colorId"), "reminders": payload.get("reminders", {}),
                 }), now, now),
            )


class PersonalGmailDraftActions:
    BASE = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"

    def __init__(self, store: Store, transport: Transport, *, capability_id: str) -> None:
        self.store = store
        self.transport = transport
        self.capability_id = capability_id

    @staticmethod
    def _validate_recipient(recipient: str) -> None:
        if any(value in recipient for value in ("\r", "\n", ",", ";")):
            raise ValueError("recipient must be one explicit address or empty")
        if recipient and "@" not in recipient:
            raise ValueError("invalid recipient")

    def create(self, *, raw_base64url: str, recipient: str = "") -> PersonalGoogleResult:
        self._validate_recipient(recipient)
        payload = self.transport("POST", self.BASE, {"message": {"raw": raw_base64url}}, None)
        provider_id = str(payload["id"])
        self._record(provider_id)
        return PersonalGoogleResult(provider_id, "gmail-draft", f"https://mail.google.com/mail/u/0/#drafts/{provider_id}")

    def update_created(self, provider_id: str, *, raw_base64url: str) -> PersonalGoogleResult:
        self._assert_owned(provider_id)
        url = f"{self.BASE}/{quote(provider_id, safe='')}"
        payload = self.transport("PUT", url, {"id": provider_id, "message": {"raw": raw_base64url}}, None)
        return PersonalGoogleResult(str(payload["id"]), "gmail-draft", f"https://mail.google.com/mail/u/0/#drafts/{provider_id}")

    def get_created(self, provider_id: str) -> dict[str, Any]:
        self._assert_owned(provider_id)
        return self.transport("GET", f"{self.BASE}/{quote(provider_id, safe='')}", None, {"format": "metadata"})

    def _assert_owned(self, provider_id: str) -> None:
        row = self.store.connection.execute(
            "SELECT created_by_jarvis,state FROM external_resources WHERE resource_id=?",
            (f"gmail-draft:{provider_id}",),
        ).fetchone()
        if not row or not row["created_by_jarvis"] or row["state"] != "active":
            raise PermissionError("draft was not created by Jarvis")

    def _record(self, provider_id: str) -> None:
        now = utc_now()
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO external_resources VALUES(?,?,?,?,?,?,?,?,?)",
                (f"gmail-draft:{provider_id}", self.capability_id, provider_id, 1,
                 None, "active", "{}", now, now),
            )
