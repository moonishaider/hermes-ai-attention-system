"""Separate, owner-only OAuth grant for bounded personal Google actions.

This token is deliberately not shared with either read-only Google connector.  The
Gmail scope is technically capable of sending, so the companion transport enforces
an exact draft-only method/path allowlist and never exposes a generic request method.
"""

from __future__ import annotations

import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import shutil
import time
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .google_offline_oauth import (
    GOOGLE_AUTHORIZATION_ENDPOINT, GOOGLE_TOKEN_ENDPOINT, GoogleOfflineOAuthError,
    _atomic_private_json, _owner_only, _scope_set, _ssl_context,
)


PERSONAL_ACTION_SCOPES = (
    "https://www.googleapis.com/auth/calendar.events.owned",
    "https://www.googleapis.com/auth/gmail.compose",
)


class PersonalGoogleActionTokenManager:
    """Maintains one separate refreshable token for Syed's personal account."""

    def __init__(self, token_root: Path | None = None, *, opener: Callable[..., Any] = urlopen,
                 now: Callable[[], float] = time.time) -> None:
        self.token_root = (token_root or Path.home() / ".hermes" / "mcp-tokens").resolve()
        self.opener, self.now = opener, now
        self.path = self.token_root / "google_personal_actions.json"

    def _load(self, path: Path) -> dict[str, Any]:
        if not _owner_only(path):
            raise GoogleOfflineOAuthError(f"Google action record is missing or not owner-only: {path.name}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GoogleOfflineOAuthError("Google action record is invalid") from exc
        if not isinstance(value, dict):
            raise GoogleOfflineOAuthError("Google action record is invalid")
        return value

    def client(self) -> dict[str, str]:
        # Reuse only the reviewed personal OAuth application identity; never its token.
        path = self.token_root / "google_personal_calendar_readonly.client.json"
        value = self._load(path)
        redirects = value.get("redirect_uris")
        if redirects != ["http://127.0.0.1:8765/callback"]:
            raise GoogleOfflineOAuthError("personal Google redirect URI is not the reviewed loopback callback")
        if not value.get("client_id") or not value.get("client_secret"):
            raise GoogleOfflineOAuthError("personal Google OAuth client is incomplete")
        return {"client_id": value["client_id"], "client_secret": value["client_secret"],
                "redirect_uri": redirects[0]}

    def authorization_request(self) -> dict[str, str]:
        client = self.client()
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
        query = urlencode({
            "client_id": client["client_id"], "redirect_uri": client["redirect_uri"],
            "response_type": "code", "scope": " ".join(PERSONAL_ACTION_SCOPES),
            "access_type": "offline", "prompt": "consent", "include_granted_scopes": "false",
            "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
            "login_hint": "moonishaider12@gmail.com",
        })
        return {"url": f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}", "state": state, "verifier": verifier}

    def _token_request(self, parameters: dict[str, str]) -> dict[str, Any]:
        request = Request(GOOGLE_TOKEN_ENDPOINT, data=urlencode(parameters).encode(), method="POST",
                          headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with self.opener(request, timeout=30, context=_ssl_context()) as response:
                value = json.loads(response.read().decode())
        except Exception as exc:
            raise GoogleOfflineOAuthError(f"personal Google token exchange failed: {type(exc).__name__}") from exc
        if not isinstance(value, dict) or not value.get("access_token"):
            raise GoogleOfflineOAuthError("personal Google token endpoint returned no access token")
        return value

    def exchange(self, *, code: str, verifier: str) -> dict[str, Any]:
        client = self.client()
        value = self._token_request({"client_id": client["client_id"], "client_secret": client["client_secret"],
            "code": code, "code_verifier": verifier, "grant_type": "authorization_code",
            "redirect_uri": client["redirect_uri"]})
        if _scope_set(value.get("scope")) != set(PERSONAL_ACTION_SCOPES) or not value.get("refresh_token"):
            raise GoogleOfflineOAuthError("Google did not grant the exact refreshable personal-action scope set")
        return value

    def install(self, value: dict[str, Any], *, backup_root: Path) -> dict[str, Any]:
        if _scope_set(value.get("scope")) != set(PERSONAL_ACTION_SCOPES):
            raise GoogleOfflineOAuthError("refusing an unexpected Google action scope")
        backup_root.mkdir(parents=True, exist_ok=False, mode=0o700)
        if self.path.exists():
            shutil.copy2(self.path, backup_root / self.path.name)
            os.chmod(backup_root / self.path.name, 0o600)
        expires = int(value.get("expires_in") or 3600)
        _atomic_private_json(self.path, {"access_token": value["access_token"],
            "refresh_token": value["refresh_token"], "expires_at": self.now() + expires,
            "expires_in": expires, "scope": " ".join(PERSONAL_ACTION_SCOPES),
            "token_type": "Bearer", "account_boundary": "personal-actions"})
        return {"connected": True, "account": "moonishaider12@gmail.com",
                "scope_count": len(PERSONAL_ACTION_SCOPES), "secrets_printed": False}

    def access_token(self) -> str:
        value = self._load(self.path)
        if _scope_set(value.get("scope")) != set(PERSONAL_ACTION_SCOPES):
            raise GoogleOfflineOAuthError("stored personal-action scopes changed")
        if float(value.get("expires_at") or 0) <= self.now() + 300:
            client = self.client()
            refreshed = self._token_request({"client_id": client["client_id"],
                "client_secret": client["client_secret"], "refresh_token": value["refresh_token"],
                "grant_type": "refresh_token"})
            value["access_token"] = refreshed["access_token"]
            value["expires_in"] = int(refreshed.get("expires_in") or 3600)
            value["expires_at"] = self.now() + value["expires_in"]
            _atomic_private_json(self.path, value)
        return str(value["access_token"])

    def status(self) -> dict[str, Any]:
        try:
            value = self._load(self.path)
            exact = _scope_set(value.get("scope")) == set(PERSONAL_ACTION_SCOPES)
            seconds_remaining = max(0, int(float(value.get("expires_at") or 0) - self.now()))
            return {"connected": exact, "account": "moonishaider12@gmail.com",
                    "refreshable": bool(value.get("refresh_token")), "exact_scopes": exact,
                    "seconds_remaining": seconds_remaining,
                    "freshness": "ready-refreshable" if value.get("refresh_token") else "reauthorization-required"}
        except GoogleOfflineOAuthError:
            return {"connected": False, "account": "moonishaider12@gmail.com",
                    "refreshable": False, "exact_scopes": False, "seconds_remaining": 0,
                    "freshness": "reauthorization-required"}
