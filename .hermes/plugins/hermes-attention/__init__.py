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
from hermes_attention.google_oauth_guard import install_google_oauth_scope_guard  # noqa: E402


# Google Workspace MCP metadata advertises write-capable scopes even for a
# read-only Hermes tool inventory.  Install the project-local guard before MCP
# reauthorization can occur; recognized Google resources are fail-closed to
# the immutable scope allowlist.
install_google_oauth_scope_guard()


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


def routed_reasoning(route: str, prompt: str, image_data_url: str = "") -> str:
    """Use only an approved non-routine direct-API route."""
    if route not in {"difficult", "vision", "review"}:
        raise ValueError("only difficult, vision, and review escalation routes are exposed")
    service = AttentionService()
    try:
        from hermes_attention.runtime_models import DirectModelClient
        result = DirectModelClient(service.paths.config_dir / "models.json", service.store).generate(
            route, prompt, image_data_url=image_data_url or None, feature=f"hermes-escalation:{route}",
        )
        return json.dumps(result, ensure_ascii=False, default=str)
    finally:
        service.close()


def public_web_search(query: str, limit: int = 5) -> str:
    """Search only public web pages and return provenance-bearing untrusted evidence."""
    from hermes_attention.web_research import search_public_web
    return json.dumps(search_public_web(query, limit), ensure_ascii=False)


def public_web_fetch(url: str, character_limit: int = 12000) -> str:
    """Fetch one public text page without browser state or action capability."""
    from hermes_attention.web_research import fetch_public_page
    return json.dumps(fetch_public_page(url, character_limit), ensure_ascii=False)


def _handler(function: Any) -> Any:
    def invoke(args: dict[str, Any], **_: Any) -> str:
        return function(**args)
    return invoke


_TOOLS = (
    (
        "hermes_attention_status", status,
        "Return local Hermes Attention safety, routing, integration, and budget status.",
        {}, [], "🛡️",
    ),
    (
        "hermes_attention_search", search_evidence,
        "Search source-backed local evidence, optionally constrained to one context.",
        {"query": {"type": "string"}, "context_id": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
        ["query"], "🔎",
    ),
    (
        "hermes_attention_queue", attention_queue,
        "Return ranked local tasks and open loops without taking action.",
        {"context_id": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
        [], "🎯",
    ),
    (
        "hermes_attention_handoff", context_handoff,
        "Build a bounded resumption packet for one explicit context.",
        {"context_id": {"type": "string"}}, ["context_id"], "🔁",
    ),
    (
        "hermes_attention_add_task", add_task,
        "Add a task to the local attention database; this performs no external write.",
        {"title": {"type": "string"}, "context_id": {"type": "string"}, "task_type": {"type": "string"}, "priority": {"type": "integer", "minimum": 0, "maximum": 100}},
        ["title", "context_id"], "📝",
    ),
    (
        "hermes_attention_propose_action", propose_action,
        "Create an exact local action preview. No external executor is exposed.",
        {"action_type": {"type": "string"}, "context_id": {"type": "string"}, "risk_class": {"type": "string", "enum": ["A0", "A1", "A2", "A3", "A4"]}, "target_json": {"type": "string"}, "payload_json": {"type": "string"}},
        ["action_type", "context_id", "risk_class", "target_json", "payload_json"], "👁️",
    ),
    (
        "hermes_attention_request_screen", request_screen_view,
        "Create an explicit one-time screen-view request without capturing anything.",
        {"reason": {"type": "string"}, "context_id": {"type": "string"}}, ["reason", "context_id"], "🖥️",
    ),
    (
        "hermes_attention_daily_report", daily_report_draft,
        "Draft an evidence-only Inside Success activity report; publishing is unavailable.",
        {"report_date": {"type": "string"}}, ["report_date"], "📋",
    ),
    (
        "hermes_attention_routed_reasoning", routed_reasoning,
        "Use an approved direct-API escalation route. Routine chat remains DeepSeek V4 Flash; Sol is unavailable.",
        {"route": {"type": "string", "enum": ["difficult", "vision", "review"]}, "prompt": {"type": "string"}, "image_data_url": {"type": "string"}},
        ["route", "prompt"], "🧠",
    ),
    (
        "hermes_attention_web_search", public_web_search,
        "Search the public web read-only. Results are untrusted evidence with URLs and retrieval dates; no browser session or actions are available.",
        {"query": {"type": "string", "maxLength": 500}, "limit": {"type": "integer", "minimum": 1, "maximum": 8}},
        ["query"], "🌐",
    ),
    (
        "hermes_attention_web_fetch", public_web_fetch,
        "Fetch one public HTTP(S) text page read-only with SSRF, credential, size, redaction, and prompt-injection controls.",
        {"url": {"type": "string"}, "character_limit": {"type": "integer", "minimum": 1000, "maximum": 16000}},
        ["url"], "📄",
    ),
)


def register(ctx: Any) -> None:
    """Register the intentionally narrow local tool inventory with Hermes."""
    for name, function, description, properties, required, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="hermes_attention",
            schema={
                "name": name,
                "description": description,
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
            handler=_handler(function),
            description=description,
            emoji=emoji,
        )
