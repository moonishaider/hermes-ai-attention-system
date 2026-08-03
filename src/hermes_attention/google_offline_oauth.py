"""Refreshable, account-scoped Google OAuth with immutable read-only scopes."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import shutil
import ssl
import tempfile
import time
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_READONLY_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
)
GOOGLE_ACCOUNTS = ("work", "personal")
GOOGLE_RESOURCES = ("gmail", "drive", "calendar")


class GoogleOfflineOAuthError(RuntimeError):
    pass


def _scope_set(value: object) -> set[str]:
    if isinstance(value, str):
        return set(value.split())
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def _owner_only(path: Path) -> bool:
    return path.is_file() and not path.stat().st_mode & 0o077


def _ssl_context() -> ssl.SSLContext:
    for candidate in (Path("/etc/ssl/cert.pem"), Path("/private/etc/ssl/cert.pem")):
        if candidate.is_file():
            return ssl.create_default_context(cafile=str(candidate))
    return ssl.create_default_context()


def _atomic_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    temporary = Path(temporary_name)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


@contextmanager
def _account_lock(token_root: Path, account: str):
    lock_path = token_root / f"google_{account}_offline_refresh.lock"
    token_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path.open("a", encoding="utf-8") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class GoogleOfflineTokenManager:
    def __init__(
        self,
        token_root: Path | None = None,
        *,
        opener: Callable[..., Any] = urlopen,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.token_root = (token_root or Path.home() / ".hermes" / "mcp-tokens").resolve()
        self.opener = opener
        self.now = now

    @staticmethod
    def token_name(account: str, resource: str) -> str:
        if account not in GOOGLE_ACCOUNTS or resource not in GOOGLE_RESOURCES:
            raise GoogleOfflineOAuthError("unsupported Google account or resource")
        return f"google_{account}_{resource}_readonly.json"

    def _load_private_json(self, path: Path) -> dict[str, Any]:
        if not _owner_only(path):
            raise GoogleOfflineOAuthError(f"Google OAuth record is missing or not owner-only: {path.name}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GoogleOfflineOAuthError(f"Google OAuth record is invalid: {path.name}") from exc
        if not isinstance(payload, dict):
            raise GoogleOfflineOAuthError(f"Google OAuth record is invalid: {path.name}")
        return payload

    def client(self, account: str) -> dict[str, Any]:
        records = []
        for resource in GOOGLE_RESOURCES:
            name = self.token_name(account, resource).removesuffix(".json") + ".client.json"
            records.append(self._load_private_json(self.token_root / name))
        identity = {(record.get("client_id"), record.get("client_secret")) for record in records}
        if len(identity) != 1 or not all(identity.pop()):
            raise GoogleOfflineOAuthError("Google account resources do not share one valid OAuth client")
        first = records[0]
        redirects = first.get("redirect_uris")
        if redirects != ["http://127.0.0.1:8765/callback"]:
            raise GoogleOfflineOAuthError("Google OAuth redirect URI differs from the reviewed loopback callback")
        return {
            "client_id": first["client_id"],
            "client_secret": first["client_secret"],
            "redirect_uri": redirects[0],
        }

    def authorization_request(self, account: str, *, login_hint: str) -> dict[str, str]:
        client = self.client(account)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
        query = urlencode({
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(GOOGLE_READONLY_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "login_hint": login_hint,
        })
        return {"url": GOOGLE_AUTHORIZATION_ENDPOINT + "?" + query, "state": state, "verifier": verifier}

    def _token_request(self, parameters: dict[str, str]) -> dict[str, Any]:
        request = Request(
            GOOGLE_TOKEN_ENDPOINT,
            data=urlencode(parameters).encode(),
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=30, context=_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GoogleOfflineOAuthError(f"Google token exchange failed: {type(exc).__name__}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
            raise GoogleOfflineOAuthError("Google token endpoint did not return a valid access token")
        return payload

    def exchange_code(self, account: str, *, code: str, verifier: str) -> dict[str, Any]:
        client = self.client(account)
        payload = self._token_request({
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": client["redirect_uri"],
        })
        if not isinstance(payload.get("refresh_token"), str) or not payload["refresh_token"]:
            raise GoogleOfflineOAuthError("Google did not issue a refresh token; offline consent was not completed")
        granted = _scope_set(payload.get("scope"))
        if granted != set(GOOGLE_READONLY_SCOPES):
            raise GoogleOfflineOAuthError("Google granted scopes differ from the immutable read-only allowlist")
        return payload

    def install_account_token(self, account: str, payload: dict[str, Any], *, backup_root: Path) -> dict[str, Any]:
        if _scope_set(payload.get("scope")) != set(GOOGLE_READONLY_SCOPES):
            raise GoogleOfflineOAuthError("refusing to store Google token with unexpected scopes")
        if not payload.get("refresh_token") or not payload.get("access_token"):
            raise GoogleOfflineOAuthError("refusing to store non-refreshable Google token")
        expires_in = int(payload.get("expires_in") or 3600)
        stored = {
            "access_token": payload["access_token"],
            "refresh_token": payload["refresh_token"],
            "expires_in": expires_in,
            "expires_at": self.now() + expires_in,
            "scope": " ".join(GOOGLE_READONLY_SCOPES),
            "token_type": payload.get("token_type") or "Bearer",
            "oauth_mode": "offline-refreshable",
            "account_boundary": account,
        }
        refresh_expires_in = int(payload.get("refresh_token_expires_in") or 0)
        if refresh_expires_in > 0:
            stored["refresh_token_expires_in"] = refresh_expires_in
            stored["refresh_token_expires_at"] = self.now() + refresh_expires_in
        backup_root.mkdir(parents=True, exist_ok=False, mode=0o700)
        os.chmod(backup_root, 0o700)
        installed = []
        for resource in GOOGLE_RESOURCES:
            destination = self.token_root / self.token_name(account, resource)
            if destination.exists():
                backup = backup_root / destination.name
                shutil.copy2(destination, backup)
                os.chmod(backup, 0o600)
            _atomic_private_json(destination, stored)
            installed.append(destination.name)
        return {
            "account": account,
            "installed_records": installed,
            "refreshable": True,
            "scope_count": len(GOOGLE_READONLY_SCOPES),
            "refresh_token_time_limited": refresh_expires_in > 0,
            "refresh_token_lifetime_seconds": refresh_expires_in or None,
            "secrets_printed": False,
        }

    def refresh_account(self, account: str, *, minimum_ttl_seconds: int = 300) -> dict[str, Any]:
        with _account_lock(self.token_root, account):
            token_paths = [self.token_root / self.token_name(account, resource) for resource in GOOGLE_RESOURCES]
            records = [self._load_private_json(path) for path in token_paths]
            refresh_tokens = {record.get("refresh_token") for record in records if record.get("refresh_token")}
            if len(refresh_tokens) != 1:
                raise GoogleOfflineOAuthError("Google account token set is not uniformly refreshable")
            if any(_scope_set(record.get("scope")) != set(GOOGLE_READONLY_SCOPES) for record in records):
                raise GoogleOfflineOAuthError("Google account token scope differs from the read-only allowlist")
            remaining = min(float(record.get("expires_at") or 0) - self.now() for record in records)
            if remaining > minimum_ttl_seconds:
                return {"account": account, "state": "ready-refreshable", "refreshed": False, "seconds_remaining": int(remaining)}
            client = self.client(account)
            refresh_token = str(next(iter(refresh_tokens)))
            payload = self._token_request({
                "client_id": client["client_id"],
                "client_secret": client["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            granted = _scope_set(payload.get("scope")) or set(GOOGLE_READONLY_SCOPES)
            if granted != set(GOOGLE_READONLY_SCOPES):
                raise GoogleOfflineOAuthError("refreshed Google token scopes differ from the read-only allowlist")
            expires_in = int(payload.get("expires_in") or 3600)
            updated = {
                **records[0],
                "access_token": payload["access_token"],
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "expires_at": self.now() + expires_in,
                "scope": " ".join(GOOGLE_READONLY_SCOPES),
                "token_type": payload.get("token_type") or records[0].get("token_type") or "Bearer",
                "oauth_mode": "offline-refreshable",
                "account_boundary": account,
            }
            refresh_expires_in = int(payload.get("refresh_token_expires_in") or 0)
            if refresh_expires_in > 0:
                updated["refresh_token_expires_in"] = refresh_expires_in
                updated["refresh_token_expires_at"] = self.now() + refresh_expires_in
            for path in token_paths:
                _atomic_private_json(path, updated)
            return {"account": account, "state": "ready-refreshable", "refreshed": True, "seconds_remaining": expires_in}

    def access_token(self, account: str, resource: str) -> str:
        self.refresh_account(account)
        payload = self._load_private_json(self.token_root / self.token_name(account, resource))
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise GoogleOfflineOAuthError("Google access token is missing after refresh")
        return token
