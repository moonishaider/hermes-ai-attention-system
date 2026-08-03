"""Read-only Google API fallback for consumer accounts excluded from Workspace MCP preview."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .google_offline_oauth import GoogleOfflineOAuthError, GoogleOfflineTokenManager


class GoogleDirectError(RuntimeError):
    pass


RESOURCE_POLICY = {
    "gmail": {
        "host": "gmail.googleapis.com",
        "scope": "https://www.googleapis.com/auth/gmail.readonly",
    },
    "drive": {
        "host": "www.googleapis.com",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
    },
    "calendar": {
        "host": "www.googleapis.com",
        "scope": {
            "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly",
        },
    },
}


def _bounded_limit(limit: int) -> int:
    return max(1, min(int(limit), 10))


def validate_google_api_url(resource: str, url: str) -> None:
    policy = RESOURCE_POLICY.get(resource)
    parsed = urlparse(url)
    if not policy or parsed.scheme != "https" or parsed.hostname != policy["host"]:
        raise GoogleDirectError("Google API request is outside the reviewed resource boundary")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise GoogleDirectError("Google API URL contains credentials or a nonstandard port")


def _ssl_context() -> ssl.SSLContext:
    for candidate in (Path("/etc/ssl/cert.pem"), Path("/private/etc/ssl/cert.pem")):
        if candidate.is_file():
            return ssl.create_default_context(cafile=str(candidate))
    return ssl.create_default_context()


class GoogleDirect:
    """Bounded GET-only client using one isolated account read-only grant."""

    def __init__(self, account: str, context: str, token_root: Path | None = None) -> None:
        if account not in {"work", "personal"} or context not in {"inside-success", "personal"}:
            raise GoogleDirectError("Unsupported Google account/context boundary")
        self.account = account
        self.context = context
        self.token_root = token_root or Path.home() / ".hermes" / "mcp-tokens"
        self.token_manager = GoogleOfflineTokenManager(self.token_root)

    def _access_token(self, resource: str) -> str:
        policy = RESOURCE_POLICY[resource]
        try:
            return self.token_manager.access_token(self.account, resource)
        except GoogleOfflineOAuthError as exc:
            raise GoogleDirectError(str(exc)) from exc

    def _request_json(self, resource: str, url: str) -> dict[str, Any]:
        validate_google_api_url(resource, url)
        request = Request(
            url,
            headers={"Authorization": "Bearer " + self._access_token(resource), "Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=20, context=_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise GoogleDirectError(f"Google {resource} read failed with HTTP {exc.code}") from exc
        except (URLError, OSError, json.JSONDecodeError) as exc:
            raise GoogleDirectError(f"Google {resource} read failed: {type(exc).__name__}") from exc
        if not isinstance(payload, dict):
            raise GoogleDirectError(f"Google {resource} returned an invalid response")
        return payload

    @staticmethod
    def _headers(message: dict[str, Any]) -> dict[str, str]:
        values: dict[str, str] = {}
        for header in message.get("payload", {}).get("headers", []):
            name = str(header.get("name") or "").lower()
            if name in {"subject", "from", "date"}:
                values[name] = str(header.get("value") or "")
        return values

    def gmail_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        limit = _bounded_limit(limit)
        query = str(query).strip()
        if not query or len(query) > 500:
            raise GoogleDirectError("Gmail query must contain 1 to 500 characters")
        listing = self._request_json("gmail", "https://gmail.googleapis.com/gmail/v1/users/me/threads?" + urlencode({"q": query, "maxResults": limit}))
        items = []
        for row in list(listing.get("threads") or [])[:limit]:
            thread_id = str(row.get("id") or "")
            if not thread_id:
                continue
            detail = self._request_json("gmail", "https://gmail.googleapis.com/gmail/v1/users/me/threads/" + quote(thread_id, safe="") + "?" + urlencode([
                ("format", "metadata"), ("metadataHeaders", "Subject"), ("metadataHeaders", "From"), ("metadataHeaders", "Date"),
            ]))
            messages = list(detail.get("messages") or [])
            latest = messages[-1] if messages else {}
            headers = self._headers(latest)
            items.append({
                "thread_id": thread_id,
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "date": headers.get("date", ""),
                "snippet": str(latest.get("snippet") or "")[:500],
                "source_ref": "https://mail.google.com/mail/u/0/#all/" + thread_id,
                "context": self.context,
            })
        return self._result("gmail", items)

    def drive_recent(self, limit: int = 10) -> dict[str, Any]:
        query = urlencode({
            "pageSize": _bounded_limit(limit),
            "orderBy": "modifiedTime desc",
            "q": "trashed = false",
            "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
        })
        payload = self._request_json("drive", "https://www.googleapis.com/drive/v3/files?" + query)
        items = [{
            "file_id": str(row.get("id") or ""),
            "name": str(row.get("name") or ""),
            "mime_type": str(row.get("mimeType") or ""),
            "modified_time": str(row.get("modifiedTime") or ""),
            "source_ref": str(row.get("webViewLink") or ("https://drive.google.com/open?id=" + str(row.get("id") or ""))),
            "context": self.context,
        } for row in list(payload.get("files") or [])[:_bounded_limit(limit)]]
        return self._result("drive", items)

    def calendar_events(self, start_time: str, end_time: str, limit: int = 10) -> dict[str, Any]:
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GoogleDirectError("Calendar bounds must be ISO 8601 timestamps") from exc
        if end <= start:
            raise GoogleDirectError("Calendar end must be after start")
        local_zone = ZoneInfo("Asia/Karachi")
        if start.tzinfo is None:
            start = start.replace(tzinfo=local_zone)
        if end.tzinfo is None:
            end = end.replace(tzinfo=local_zone)
        query = urlencode({
            "timeMin": start.isoformat(), "timeMax": end.isoformat(), "singleEvents": "true",
            "orderBy": "startTime", "maxResults": _bounded_limit(limit),
        })
        payload = self._request_json("calendar", "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + query)
        items = [{
            "event_id": str(row.get("id") or ""),
            "summary": str(row.get("summary") or ""),
            "start": row.get("start", {}).get("dateTime") or row.get("start", {}).get("date"),
            "end": row.get("end", {}).get("dateTime") or row.get("end", {}).get("date"),
            "status": str(row.get("status") or ""),
            "source_ref": str(row.get("htmlLink") or ""),
            "context": self.context,
        } for row in list(payload.get("items") or [])[:_bounded_limit(limit)]]
        return self._result("calendar", items)

    def _result(self, resource: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        connection_id = f"google_{self.account}_{resource}_readonly"
        return {
            "connection_id": connection_id,
            "source_system": connection_id,
            "mode": "read-only-direct-api",
            "account_boundary": self.account,
            "context": self.context,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "items": items,
            "count": len(items),
            "writes_available": False,
        }


class PersonalGoogleDirect(GoogleDirect):
    def __init__(self, token_root: Path | None = None) -> None:
        super().__init__("personal", "personal", token_root)


class WorkGoogleDirect(GoogleDirect):
    def __init__(self, token_root: Path | None = None) -> None:
        super().__init__("work", "inside-success", token_root)
