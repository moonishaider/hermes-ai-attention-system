#!/usr/bin/env python3
"""Disable unsupported consumer Workspace MCP servers; use project direct read tools."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

import yaml


PERSONAL_MCP_SERVERS = (
    "google_personal_gmail_readonly",
    "google_personal_drive_readonly",
    "google_personal_calendar_readonly",
)


def main() -> int:
    home = Path.home() / ".hermes"
    config_path = home / "config.yaml"
    if not config_path.is_file() or config_path.stat().st_mode & 0o077:
        raise SystemExit("Hermes config is missing or not owner-only")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = home / "backups" / f"prompt4-personal-google-direct-{timestamp}"
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(config_path, backup_dir / "config.yaml")
    os.chmod(backup_dir / "config.yaml", 0o600)

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    servers = data.get("mcp_servers", {})
    missing = [name for name in PERSONAL_MCP_SERVERS if name not in servers]
    if missing:
        raise SystemExit("Missing personal Google MCP records: " + ",".join(missing))
    for name in PERSONAL_MCP_SERVERS:
        servers[name]["enabled"] = False

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
        "disabled_unsupported_personal_mcp_servers": list(PERSONAL_MCP_SERVERS),
        "direct_read_tools": 3,
        "backup": str(backup_dir),
        "secrets_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
