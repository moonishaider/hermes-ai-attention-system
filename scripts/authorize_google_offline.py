#!/usr/bin/env python3
"""Obtain one refreshable combined read-only Google grant for an account."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.google_offline_oauth import GoogleOfflineOAuthError, GoogleOfflineTokenManager  # noqa: E402


class CallbackHandler(BaseHTTPRequestHandler):
    result: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return
        values = parse_qs(parsed.query)
        self.__class__.result = {key: rows[0] for key, rows in values.items() if rows}
        body = b"Google authorization received. You can return to Codex."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True, choices=("work", "personal"))
    parser.add_argument("--login-hint", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    arguments = parser.parse_args()
    manager = GoogleOfflineTokenManager()
    request = manager.authorization_request(arguments.account, login_hint=arguments.login_hint)
    print(json.dumps({
        "action": "Open authorization_url in the correct Chrome profile, confirm the account and four read-only scopes, then approve once.",
        "account": arguments.account,
        "authorization_url": request["url"],
        "temporary_callback": "http://127.0.0.1:8765/callback",
        "secrets_printed": False,
    }, sort_keys=True), flush=True)
    server = HTTPServer(("127.0.0.1", 8765), CallbackHandler)
    server.timeout = max(60, min(arguments.timeout_seconds, 600))
    try:
        server.handle_request()
    finally:
        server.server_close()
    result = CallbackHandler.result
    if result.get("error"):
        raise GoogleOfflineOAuthError("Google authorization was denied or failed")
    if not hmac.compare_digest(result.get("state", ""), request["state"]):
        raise GoogleOfflineOAuthError("Google OAuth callback state did not match")
    code = result.get("code")
    if not code:
        raise GoogleOfflineOAuthError("Google OAuth callback did not contain an authorization code")
    payload = manager.exchange_code(arguments.account, code=code, verifier=request["verifier"])
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = Path.home() / ".hermes" / "backups" / f"google-offline-{arguments.account}-{timestamp}"
    installed = manager.install_account_token(arguments.account, payload, backup_root=backup)
    proof = manager.refresh_account(arguments.account, minimum_ttl_seconds=7200)
    print(json.dumps({
        **installed,
        "automatic_refresh_proved": proof["refreshed"],
        "backup": str(backup),
        "authorization_url_printed_once": True,
        "token_values_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
