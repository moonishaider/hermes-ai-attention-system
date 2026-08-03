#!/usr/bin/env python3
"""Trigger and verify Google Workspace MCP OAuth without printing source data.

Google's Developer Preview MCP servers currently allow unauthenticated
``initialize`` and ``tools/list`` calls.  Hermes v0.19.1's ``mcp login`` command
therefore returns before OAuth has produced a token.  This operational helper
calls one allowlisted read-only tool so the provider emits the real OAuth
challenge, then reports metadata only.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_attention.google_oauth_guard import install_google_oauth_scope_guard, validated_read_probe_blocks


READ_ONLY_PROBES = {
    "google_work_gmail_readonly": ("list_labels", {}),
    "google_work_drive_readonly": ("list_recent_files", {"page_size": 1}),
    "google_work_calendar_readonly": ("list_calendars", {}),
    "google_personal_gmail_readonly": ("list_labels", {}),
    "google_personal_drive_readonly": ("list_recent_files", {"page_size": 1}),
    "google_personal_calendar_readonly": ("list_calendars", {}),
}


async def run_probe(connector: str) -> tuple[str, int, str]:
    from hermes_cli.config import load_config
    from hermes_cli.env_loader import load_hermes_dotenv
    from hermes_cli.mcp_config import _resolve_mcp_server_config
    from tools.mcp_oauth import force_interactive_oauth
    from tools.mcp_tool import _connect_server

    load_hermes_dotenv(hermes_home=Path.home() / ".hermes")
    if not install_google_oauth_scope_guard():
        raise RuntimeError("MCP OAuth SDK is unavailable; refusing unguarded Google OAuth")
    config = load_config().get("mcp_servers", {}).get(connector)
    if not isinstance(config, dict):
        raise RuntimeError(f"unknown connector: {connector}")
    config = _resolve_mcp_server_config(config)
    tool_name, arguments = READ_ONLY_PROBES[connector]

    with force_interactive_oauth():
        server = await _connect_server(connector, config)
        try:
            result = await server.session.call_tool(tool_name, arguments)
            blocks = validated_read_probe_blocks(result)
            digest = hashlib.sha256(repr(blocks).encode("utf-8")).hexdigest()[:16]
            return tool_name, len(blocks), digest
        finally:
            await server.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("connector", choices=sorted(READ_ONLY_PROBES))
    args = parser.parse_args()
    tool_name, block_count, digest = asyncio.run(run_probe(args.connector))
    print(
        f"OAuth read-only probe passed: connector={args.connector} "
        f"tool={tool_name} content_blocks={block_count} digest={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
