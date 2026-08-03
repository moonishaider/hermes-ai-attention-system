"""Strict-scope user OAuth for the official Zoom MCP server."""

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


class ZoomOAuthError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ZoomOAuthConnection:
    display_name: str
    client_id_env: str
    server_name: str
    server_url: str
    authorization_endpoint: str
    token_endpoint: str
    redirect_uri: str
    scopes: tuple[str, ...]
    tools_include: tuple[str, ...]
    tools_exclude: tuple[str, ...]


def load_zoom_connection(config_path: Path | None = None) -> ZoomOAuthConnection:
    path = config_path or ProjectPaths.discover().config_dir / "connectors" / "zoom_oauth_client.json"
    raw = load_json(path)
    scopes = tuple(str(value) for value in raw.get("scopes", ()))
    tools_include = tuple(str(value) for value in raw.get("tools_include", ()))
    tools_exclude = tuple(str(value) for value in raw.get("tools_exclude", ()))
    if not scopes or not tools_include:
        raise ZoomOAuthError("Zoom scope/tool allowlist is empty")
    if any(":write:" in scope or scope.endswith(":write") for scope in scopes):
        raise ZoomOAuthError("Zoom configuration contains a write scope")
    return ZoomOAuthConnection(
        display_name=str(raw["display_name"]),
        client_id_env=str(raw["client_id_env"]),
        server_name=str(raw["server_name"]),
        server_url=str(raw["server_url"]),
        authorization_endpoint=str(raw["authorization_endpoint"]),
        token_endpoint=str(raw["token_endpoint"]),
        redirect_uri=str(raw["redirect_uri"]),
        scopes=scopes,
        tools_include=tools_include,
        tools_exclude=tools_exclude,
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


def build_zoom_authorization_url(connection: ZoomOAuthConnection, client_id: str, state: str, code_verifier: str) -> str:
    return connection.authorization_endpoint + "?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": connection.redirect_uri,
        "state": state,
        "code_challenge": _b64url_digest(code_verifier),
        "code_challenge_method": "S256",
        "scope": " ".join(connection.scopes),
    })


def validate_zoom_granted_scopes(requested: tuple[str, ...], granted: str | list[str] | None) -> tuple[str, ...]:
    granted_items = tuple(item for item in granted.replace(",", " ").split() if item) if isinstance(granted, str) else tuple(granted or ())
    if not granted_items:
        raise ZoomOAuthError("Zoom returned no granted scopes")
    extras = sorted(set(granted_items) - set(requested))
    missing = sorted(set(requested) - set(granted_items))
    if extras:
        raise ZoomOAuthError("Zoom granted scopes outside the reviewed allowlist: " + ",".join(extras))
    if missing:
        raise ZoomOAuthError("Zoom omitted requested scopes: " + ",".join(missing))
    return granted_items


def _ssl_context() -> ssl.SSLContext:
    for candidate in (Path("/etc/ssl/cert.pem"), Path("/private/etc/ssl/cert.pem")):
        if candidate.is_file():
            return ssl.create_default_context(cafile=str(candidate))
    return ssl.create_default_context()


def _exchange_code(connection: ZoomOAuthConnection, client_id: str, code: str, code_verifier: str) -> dict[str, Any]:
    request = Request(
        connection.token_endpoint,
        data=urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": connection.redirect_uri,
            "code_verifier": code_verifier,
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30, context=_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        raise ZoomOAuthError(f"Zoom token exchange failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise ZoomOAuthError("Zoom token exchange returned no access token")
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


def persist_zoom_oauth_state(
    connection: ZoomOAuthConnection,
    client_id: str,
    token_payload: dict[str, Any],
    token_dir: Path | None = None,
) -> dict[str, Any]:
    granted = validate_zoom_granted_scopes(connection.scopes, token_payload.get("scope"))
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ZoomOAuthError("Zoom token response omitted access_token")
    token: dict[str, Any] = {
        "access_token": access_token,
        "token_type": str(token_payload.get("token_type") or "Bearer"),
        "scope": " ".join(granted),
    }
    refresh_token = token_payload.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        token["refresh_token"] = refresh_token
    expires_in = int(token_payload.get("expires_in") or 0)
    if expires_in > 0:
        token["expires_in"] = expires_in
        token["expires_at"] = time.time() + expires_in

    base = token_dir or Path.home() / ".hermes" / "mcp-tokens"
    token_path = base / f"{connection.server_name}.json"
    _atomic_json(token_path, token)
    _atomic_json(base / f"{connection.server_name}.client.json", {
        "client_id": client_id,
        "client_name": connection.display_name,
        "redirect_uris": [connection.redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": " ".join(connection.scopes),
        "token_endpoint_auth_method": "none",
    })
    _atomic_json(base / f"{connection.server_name}.meta.json", {
        "issuer": "https://zoom.us",
        "authorization_endpoint": connection.authorization_endpoint,
        "token_endpoint": connection.token_endpoint,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(connection.scopes),
    })
    return {
        "stored": True,
        "server_name": connection.server_name,
        "granted_scopes": sorted(granted),
        "refreshable": bool(refresh_token),
        "token_path": str(token_path),
        "secret_printed": False,
        "token_printed": False,
    }


def strict_zoom_oauth_login(timeout_seconds: int = 240) -> dict[str, Any]:
    connection = load_zoom_connection()
    client_id = _load_env_value(connection.client_id_env)
    if not client_id:
        raise ZoomOAuthError("Zoom public OAuth client ID is not configured")
    parsed = urlparse(connection.redirect_uri)
    if parsed.hostname != "localhost" or parsed.path not in ("", "/") or not parsed.port:
        raise ZoomOAuthError("Zoom redirect URI must be the fixed localhost callback")

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(72)
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed_request = urlparse(self.path)
            if parsed_request.path in ("", "/"):
                query = parse_qs(parsed_request.query)
                result["state"] = query.get("state", [""])[0]
                result["code"] = query.get("code", [""])[0]
                result["error"] = query.get("error", [""])[0]
            body = b"Hermes Zoom authorization received. You may close this tab."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", parsed.port), CallbackHandler)
    server.timeout = 1
    authorization_url = build_zoom_authorization_url(connection, client_id, state, code_verifier)
    print(json.dumps({
        "authorization_required": True,
        "connection": connection.server_name,
        "authorization_url": authorization_url,
        "requested_scope_count": len(connection.scopes),
        "write_scopes_requested": False,
    }), flush=True)

    deadline = time.monotonic() + max(30, timeout_seconds)
    try:
        while time.monotonic() < deadline and not result:
            server.handle_request()
    finally:
        server.server_close()
    if not result:
        raise ZoomOAuthError("Zoom OAuth callback timed out")
    if result.get("error"):
        raise ZoomOAuthError("Zoom authorization was denied: " + result["error"])
    if not secrets.compare_digest(result.get("state", ""), state) or not result.get("code"):
        raise ZoomOAuthError("Zoom OAuth callback state/code validation failed")

    payload = _exchange_code(connection, client_id, result["code"], code_verifier)
    return persist_zoom_oauth_state(connection, client_id, payload)
