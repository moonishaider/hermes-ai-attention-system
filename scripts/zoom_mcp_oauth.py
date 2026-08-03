#!/usr/bin/env python3
"""Authorize or metadata-probe the strict read-only Zoom MCP connection."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_attention.zoom_oauth import load_zoom_connection, strict_zoom_oauth_login


async def probe() -> dict[str, object]:
    from hermes_cli.config import load_config
    from hermes_cli.env_loader import load_hermes_dotenv
    from hermes_cli.mcp_config import _resolve_mcp_server_config
    from tools.mcp_tool import _connect_server

    connection = load_zoom_connection()
    load_hermes_dotenv(hermes_home=Path.home() / ".hermes")
    raw = load_config().get("mcp_servers", {}).get(connection.server_name)
    if not isinstance(raw, dict):
        raise RuntimeError("Zoom runtime connector is not installed")
    server = await _connect_server(connection.server_name, _resolve_mcp_server_config(raw))
    try:
        result = await server.session.list_tools()
        names = sorted(tool.name for tool in result.tools)
        smoke = await server.session.call_tool("recordings_list", {
            "from": "2026-08-01",
            "to": "2026-08-04",
            "page_size": 1,
        })
        blocks = list(getattr(smoke, "content", None) or [])
        smoke_digest = hashlib.sha256(repr(blocks).encode("utf-8")).hexdigest()[:16]
    finally:
        await server.shutdown()
    missing = sorted(set(connection.tools_include) - set(names))
    if missing:
        raise RuntimeError("Zoom MCP is missing reviewed read tools: " + ",".join(missing))
    return {
        "connected": True,
        "raw_tool_count": len(names),
        "reviewed_tools_present": sorted(connection.tools_include),
        "provider_write_tools_present_but_not_exposed": sorted(set(names) & set(connection.tools_exclude)),
        "runtime_include_count": len(connection.tools_include),
        "metadata_smoke": "recordings_list",
        "metadata_content_blocks": len(blocks),
        "metadata_digest": smoke_digest,
        "source_content_printed": False,
        "tokens_printed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("login", "probe"))
    arguments = parser.parse_args()
    result = strict_zoom_oauth_login() if arguments.action == "login" else asyncio.run(probe())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
