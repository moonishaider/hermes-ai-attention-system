#!/usr/bin/env python3
"""One explicit loopback OAuth flow for Jarvis personal Calendar/draft actions."""

from __future__ import annotations

from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.personal_google_action_oauth import PersonalGoogleActionTokenManager


def main() -> int:
    manager = PersonalGoogleActionTokenManager()
    request = manager.authorization_request()
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            values = parse_qs(parsed.query)
            if parsed.path != "/callback" or values.get("state", [""])[0] != request["state"]:
                self.send_response(400); self.end_headers(); return
            result["code"] = values.get("code", [""])[0]
            result["error"] = values.get("error", [""])[0]
            self.send_response(200 if result["code"] else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(b"<h2>Jarvis personal actions authorization received.</h2><p>You may return to Jarvis.</p>")

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 8765), Callback)
    # Browsers may probe the loopback origin or request a favicon before the
    # real OAuth redirect. Keep accepting requests until one valid state-bound
    # callback arrives, or until the deliberate owner-review window expires.
    server.timeout = 1
    print(json.dumps({"ok": True, "authorizationUrl": request["url"],
                      "account": "moonishaider12@gmail.com", "secretsPrinted": False}), flush=True)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline and not result.get("code") and not result.get("error"):
        server.handle_request()
    server.server_close()
    if not result.get("code"):
        raise RuntimeError(f"Google authorization did not complete: {result.get('error') or 'timeout'}")
    token = manager.exchange(code=result["code"], verifier=request["verifier"])
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    installed = manager.install(token, backup_root=Path.home() / ".hermes" / "backups" /
                                f"google-personal-actions-before-{stamp}")
    print(json.dumps({"ok": True, **installed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error), "secretsPrinted": False}), flush=True)
        raise SystemExit(2)
