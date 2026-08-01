"""Hermes plugin adapter. It deliberately exposes no external action executor."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_attention.service import AttentionService  # noqa: E402


def _call(method: str, **kwargs: Any) -> str:
    service = AttentionService()
    try:
        result = getattr(service, method)(**kwargs)
        return json.dumps(result, sort_keys=True, default=str)
    finally:
        service.close()


def status() -> str:
    """Return runtime safety, routing, integration, and budget status."""
    return _call("status")


def search_evidence(query: str, context_id: str = "", limit: int = 10) -> str:
    """Search source-backed evidence, optionally inside one context."""
    return _call("search", query=query, context_id=context_id or None, limit=limit)


def attention_queue(context_id: str = "", limit: int = 10) -> str:
    """Rank open loops and tasks without performing them."""
    return _call("attention_queue", context_id=context_id or None, limit=limit)


def context_handoff(context_id: str) -> str:
    """Return a bounded resumption packet for an explicit context."""
    return _call("context_handoff", context_id=context_id)


def add_task(title: str, context_id: str, task_type: str = "task", priority: int = 50) -> str:
    """Add a local task; this performs no external write."""
    return _call("add_task", title=title, context_id=context_id, task_type=task_type, priority=priority)


def propose_action(action_type: str, context_id: str, risk_class: str, target_json: str, payload_json: str) -> str:
    """Create an exact local preview. No executor is exposed by this plugin."""
    return _call(
        "propose_action",
        action_type=action_type,
        context_id=context_id,
        risk_class=risk_class,
        target=json.loads(target_json),
        payload=json.loads(payload_json),
    )


def request_screen_view(reason: str, context_id: str) -> str:
    """Request explicit local capture; this function does not capture a screen."""
    return _call("request_screen_view", reason=reason, context_id=context_id)


def daily_report_draft(report_date: str) -> str:
    """Create a local source-backed draft; publishing is unavailable."""
    return _call("daily_report_draft", report_date=report_date)


def register(ctx: Any) -> None:
    """Register the intentionally narrow local tool inventory with Hermes."""
    for tool in (
        status,
        search_evidence,
        attention_queue,
        context_handoff,
        add_task,
        propose_action,
        request_screen_view,
        daily_report_draft,
    ):
        ctx.register_tool(tool)
