#!/usr/bin/env python3
"""Safely merge the reviewed Zoom MCP connection into ~/.hermes/config.yaml."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_attention.zoom_oauth import load_zoom_connection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true", help="enable only after OAuth and inventory verification")
    arguments = parser.parse_args()
    connection = load_zoom_connection()
    home = Path.home() / ".hermes"
    config_path = home / "config.yaml"
    credentials_path = home / "credentials" / "zoom-work-mcp.json"
    if not config_path.is_file() or not credentials_path.is_file():
        raise SystemExit("Hermes config or owner-only Zoom credentials are missing")
    if credentials_path.stat().st_mode & 0o077:
        raise SystemExit("Zoom credentials are not owner-only")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    if credentials.get("redirect_uri") != connection.redirect_uri or not credentials.get("public_client_id"):
        raise SystemExit("Zoom credential/config redirect mismatch")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = home / "backups" / f"prompt4-zoom-config-{timestamp}"
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(config_path, backup_dir / "config.yaml")
    os.chmod(backup_dir / "config.yaml", 0o600)

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    servers = data.setdefault("mcp_servers", {})
    servers[connection.server_name] = {
        "url": connection.server_url,
        "auth": "oauth",
        "oauth": {
            "client_id": "${ZOOM_WORK_OAUTH_PUBLIC_CLIENT_ID}",
            "scope": " ".join(connection.scopes),
            "redirect_uri": connection.redirect_uri,
            "redirect_port": 8767,
            "redirect_host": "127.0.0.1",
            "token_endpoint_auth_method": "none",
            "client_name": connection.display_name,
        },
        "enabled": bool(arguments.enable),
        # Zoom's notification GET stream is recycled before Hermes' default
        # three-minute liveness probe. Its generic ping path also recycles the
        # session, so use a metadata-only tools/list proof before the provider
        # recycle can exhaust the rapid-drop budget and park the read tools.
        "keepalive_interval": 15,
        "keepalive_probe": "list_tools",
        "tools": {
            "include": list(connection.tools_include),
            "resources": False,
            "prompts": False,
        },
    }
    handle, temporary = tempfile.mkstemp(prefix="config.yaml.", suffix=".tmp", dir=home)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False)
        os.chmod(temporary, 0o600)
        os.replace(temporary, config_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(json.dumps({
        "installed": True,
        "enabled": bool(arguments.enable),
        "server_name": connection.server_name,
        "runtime_tool_count": len(connection.tools_include),
        "backup": str(backup_dir),
        "secrets_printed": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
