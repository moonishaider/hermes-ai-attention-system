"""Strict-scope Slack OAuth for the hosted MCP server.

The pinned MCP SDK replaces a configured scope with every scope advertised by
Slack's protected-resource metadata. That includes write scopes. This adapter
keeps the reviewed project allowlist authoritative, rejects any extra granted
scope, and persists only Hermes-compatible mode-600 OAuth state.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import ssl
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .config import ProjectPaths, load_json


class SlackOAuthError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SlackOAuthConnection:
    name: str
    display_name: str
    app_id: str
    client_id: str
    client_secret_env: str
    server_name: str
    server_url: str
    resource: str
    authorization_endpoint: str
    token_endpoint: str
    redirect_uri: str
    scopes: tuple[str, ...]


def load_connection(name: str, config_path: Path | None = None) -> SlackOAuthConnection:
    path = config_path or ProjectPaths.discover().config_dir / "connectors" / "slack_oauth_clients.json"
    raw = load_json(path).get("connections", {}).get(name)
    if not isinstance(raw, dict):
        raise SlackOAuthError(f"unknown Slack OAuth connection: {name}")
    scopes = tuple(str(item) for item in raw.get("scopes", []))
    if not scopes or any(not item for item in scopes):
        raise SlackOAuthError("Slack OAuth scope allowlist is empty or malformed")
    return SlackOAuthConnection(
        name=name,
        display_name=str(raw["display_name"]),
        app_id=str(raw["app_id"]),
        client_id=str(raw["client_id"]),
        client_secret_env=str(raw["client_secret_env"]),
        server_name=str(raw["server_name"]),
        server_url=str(raw["server_url"]),
        resource=str(raw["resource"]),
        authorization_endpoint=str(raw["authorization_endpoint"]),
        token_endpoint=str(raw["token_endpoint"]),
        redirect_uri=str(raw["redirect_uri"]),
        scopes=scopes,
    )


def _load_env_value(name: str, env_path: Path | None = None) -> str:
    if os.environ.get(name):
        return os.environ[name].strip()
    path = env_path or Path.home() / ".hermes" / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip()
    return ""


def _b64url_digest(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_authorization_url(connection: SlackOAuthConnection, state: str, code_verifier: str) -> str:
    params = {
        "response_type": "code",
        "client_id": connection.client_id,
        "redirect_uri": connection.redirect_uri,
        "state": state,
        "code_challenge": _b64url_digest(code_verifier),
        "code_challenge_method": "S256",
        "resource": connection.resource,
        "scope": " ".join(connection.scopes),
    }
    return connection.authorization_endpoint + "?" + urlencode(params)


def validate_granted_scopes(requested: tuple[str, ...], granted: str | list[str] | None) -> tuple[str, ...]:
    granted_items = tuple(item for item in granted.replace(",", " ").split() if item) if isinstance(granted, str) else tuple(granted or ())
    extras = sorted(set(granted_items) - set(requested))
    if extras:
        raise SlackOAuthError("provider granted scopes outside the read-only allowlist: " + ",".join(extras))
    if not granted_items:
        raise SlackOAuthError("provider returned no granted scopes")
    return granted_items


def _ssl_context() -> ssl.SSLContext:
    for candidate in (Path("/etc/ssl/cert.pem"), Path("/private/etc/ssl/cert.pem")):
        if candidate.is_file():
            return ssl.create_default_context(cafile=str(candidate))
    return ssl.create_default_context()


def _post_form(url: str, fields: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30, context=_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        raise SlackOAuthError(f"Slack token exchange failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict) or payload.get("ok") is False:
        error = str(payload.get("error", "provider rejected token exchange")) if isinstance(payload, dict) else "invalid provider response"
        raise SlackOAuthError(f"Slack token exchange rejected: {error}")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _extract_token(payload: dict[str, Any]) -> dict[str, Any]:
    user = payload.get("authed_user") if isinstance(payload.get("authed_user"), dict) else {}
    access_token = payload.get("access_token") or user.get("access_token")
    refresh_token = payload.get("refresh_token") or user.get("refresh_token")
    scope = payload.get("scope") or user.get("scope")
    expires_in = payload.get("expires_in") or user.get("expires_in")
    if not isinstance(access_token, str) or not access_token:
        raise SlackOAuthError("Slack token response omitted access_token")
    result: dict[str, Any] = {
        "access_token": access_token,
        "token_type": str(payload.get("token_type") or user.get("token_type") or "Bearer"),
        "scope": scope,
    }
    if isinstance(refresh_token, str) and refresh_token:
        result["refresh_token"] = refresh_token
    if expires_in is not None:
        result["expires_in"] = int(expires_in)
        result["expires_at"] = time.time() + int(expires_in)
    return result


def persist_hermes_oauth_state(
    connection: SlackOAuthConnection,
    client_secret: str,
    token_payload: dict[str, Any],
    token_dir: Path | None = None,
) -> dict[str, Any]:
    token = _extract_token(token_payload)
    granted = validate_granted_scopes(connection.scopes, token.get("scope"))
    base = token_dir or Path.home() / ".hermes" / "mcp-tokens"
    token_path = base / f"{connection.server_name}.json"
    client_path = base / f"{connection.server_name}.client.json"
    meta_path = base / f"{connection.server_name}.meta.json"
    _atomic_json(token_path, token)
    _atomic_json(client_path, {
        "client_id": connection.client_id,
        "client_secret": client_secret,
        "client_name": connection.display_name,
        "redirect_uris": [connection.redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": " ".join(connection.scopes),
        "token_endpoint_auth_method": "client_secret_post",
    })
    _atomic_json(meta_path, {
        "issuer": connection.resource,
        "authorization_endpoint": connection.authorization_endpoint,
        "token_endpoint": connection.token_endpoint,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": list(connection.scopes),
    })
    return {
        "stored": True,
        "server_name": connection.server_name,
        "granted_scopes": sorted(granted),
        "missing_requested_scopes": sorted(set(connection.scopes) - set(granted)),
        "token_path": str(token_path),
        "secret_printed": False,
        "token_printed": False,
    }


def strict_slack_oauth_login(connection_name: str, timeout_seconds: int = 240) -> dict[str, Any]:
    connection = load_connection(connection_name)
    client_secret = _load_env_value(connection.client_secret_env)
    if not client_secret:
        raise SlackOAuthError(f"missing {connection.client_secret_env}")
    parsed = urlparse(connection.redirect_uri)
    if parsed.hostname != "127.0.0.1" or parsed.path != "/callback" or not parsed.port:
        raise SlackOAuthError("redirect URI must be a fixed 127.0.0.1 callback")

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(72)
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            query = parse_qs(urlparse(self.path).query)
            if urlparse(self.path).path == "/callback":
                result["state"] = query.get("state", [""])[0]
                result["code"] = query.get("code", [""])[0]
                result["error"] = query.get("error", [""])[0]
            body = b"Hermes Slack authorization received. You may close this tab."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", parsed.port), CallbackHandler)
    server.timeout = 1
    authorization_url = build_authorization_url(connection, state, code_verifier)
    print(json.dumps({
        "authorization_required": True,
        "connection": connection.name,
        "authorization_url": authorization_url,
        "requested_scopes": list(connection.scopes),
        "write_scopes_requested": False,
    }), flush=True)

    deadline = time.monotonic() + max(30, timeout_seconds)
    try:
        while time.monotonic() < deadline and not result:
            server.handle_request()
    finally:
        server.server_close()
    if not result:
        raise SlackOAuthError("Slack OAuth callback timed out")
    if result.get("error"):
        raise SlackOAuthError("Slack authorization was denied: " + result["error"])
    if not secrets.compare_digest(result.get("state", ""), state) or not result.get("code"):
        raise SlackOAuthError("Slack OAuth callback state/code validation failed")

    payload = _post_form(connection.token_endpoint, {
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": connection.redirect_uri,
        "client_id": connection.client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier,
        "resource": connection.resource,
    })
    return persist_hermes_oauth_state(connection, client_secret, payload)
