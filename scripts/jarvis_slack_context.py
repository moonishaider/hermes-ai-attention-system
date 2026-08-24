#!/usr/bin/env python3
"""Fetch bounded read-only Slack evidence for one Jarvis turn.

The helper is intentionally narrow: it accepts a context and a recent-window
size, calls only the reviewed Slack search tool, and returns evidence to the
native process over stdout. It never writes to Slack or prints credentials.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any


CONNECTIONS = {
    "inside-success": "slack_inside_success_readonly",
    "mitchell": "slack_mitchell_readonly",
}
MAX_EVIDENCE_CHARS = 24_000


def _read_request() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    return value


def _content_text(block: object) -> str:
    text = getattr(block, "text", None)
    if isinstance(text, str):
        return text
    model_dump = getattr(block, "model_dump", None)
    if callable(model_dump):
        value = model_dump()
        if isinstance(value, dict) and isinstance(value.get("text"), str):
            return value["text"]
    return ""


async def fetch(request: dict[str, Any]) -> dict[str, Any]:
    context = str(request.get("context") or "").strip().lower()
    server_name = CONNECTIONS.get(context)
    if not server_name:
        raise ValueError("Slack evidence requires one reviewed client context")
    days = int(request.get("days") or 2)
    if days < 1 or days > 7:
        raise ValueError("recent window must be between 1 and 7 days")

    from hermes_cli.config import load_config
    from hermes_cli.env_loader import load_hermes_dotenv
    from hermes_cli.mcp_config import _resolve_mcp_server_config
    from tools.mcp_tool import _connect_server

    load_hermes_dotenv(hermes_home=Path.home() / ".hermes")
    raw = (load_config().get("mcp_servers") or {}).get(server_name)
    if not isinstance(raw, dict) or raw.get("enabled") is not True:
        raise RuntimeError("reviewed Slack connection is not enabled")
    included = set(((raw.get("tools") or {}).get("include") or []))
    tool_name = "slack_search_public_and_private"
    if tool_name not in included:
        raise RuntimeError("reviewed Slack search tool is not allowlisted")

    after_date = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    server = await _connect_server(server_name, _resolve_mcp_server_config(raw))
    try:
        result = await server.session.call_tool(
            tool_name,
            {
                "query": f"after:{after_date}",
                "limit": 20,
                "sort": "timestamp",
                "sort_dir": "desc",
                "response_format": "concise",
                "include_context": True,
                "max_context_length": 1200,
                "only_my_channels": True,
                "include_bots": False,
                "content_types": "messages",
            },
        )
        if bool(getattr(result, "isError", False)):
            raise RuntimeError("Slack returned a read error")
        text = "\n".join(filter(None, (_content_text(block) for block in (getattr(result, "content", None) or []))))
    finally:
        await server.shutdown()

    return {
        "ok": True,
        "connection": server_name,
        "tool": tool_name,
        "after": after_date,
        "evidence": text[:MAX_EVIDENCE_CHARS],
        "truncated": len(text) > MAX_EVIDENCE_CHARS,
        "write_capability": False,
    }


def main() -> int:
    try:
        result = asyncio.run(fetch(_read_request()))
    except Exception as error:
        # Keep credentials, stack traces, and provider internals out of the
        # native app while returning a machine-readable fail-closed result.
        print(json.dumps({"ok": False, "error": str(error)[:240]}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
