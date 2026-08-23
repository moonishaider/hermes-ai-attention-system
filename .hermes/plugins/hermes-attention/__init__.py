"""Hermes plugin adapter. It deliberately exposes no external action executor."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_attention.config import ProjectPaths  # noqa: E402
from hermes_attention.service import AttentionService  # noqa: E402
from hermes_attention.google_oauth_guard import install_google_oauth_scope_guard  # noqa: E402
from hermes_attention.hermes_voice_compat import install_voice_playback_interrupt_guard  # noqa: E402
from hermes_attention.overlay_runtime_bridge import install_overlay_runtime_bridge  # noqa: E402


# Google Workspace MCP metadata advertises write-capable scopes even for a
# read-only Hermes tool inventory.  Install the project-local guard before MCP
# reauthorization can occur; recognized Google resources are fail-closed to
# the immutable scope allowlist.
install_google_oauth_scope_guard()
PROJECT_PATHS = ProjectPaths.discover(ROOT)

def _hermes_version_tuple() -> tuple[int, int, int]:
    """Return the installed Hermes version without importing runtime internals."""
    try:
        raw = version("hermes-agent")
    except PackageNotFoundError:
        return (0, 0, 0)
    parts = [int(value) for value in re.findall(r"\d+", raw)[:3]]
    return tuple((parts + [0, 0, 0])[:3])


# Hermes 0.19.1 restarts interrupted macOS afplay output through its ffplay
# fallback. The official 0.20.0 voice stack fixes barge-in natively, so the
# compatibility patch must never replace its redesigned playback path.
if _hermes_version_tuple() < (0, 20, 0):
    install_voice_playback_interrupt_guard()


def _call(method: str, **kwargs: Any) -> str:
    service = AttentionService(paths=PROJECT_PATHS)
    try:
        result = getattr(service, method)(**kwargs)
        return json.dumps(result, sort_keys=True, default=str)
    finally:
        service.close()


def status() -> str:
    """Return runtime safety, routing, integration, and budget status."""
    return _call("status")


def search_evidence(query: str, context_id: str = "", limit: int = 10) -> str:
    """Search evidence; current-work intents first refresh recent Codex chats."""
    return _call("search", query=query, context_id=context_id or None, limit=limit)


def sync_codex(
    lookback_days: int = 14,
    maximum_threads: int = 50,
    maximum_items: int = 2000,
    max_threads: int | None = None,
) -> str:
    """Read recent Codex chats through the official local read-only interface."""
    # Calls created before the canonical schema rename can still contain the
    # legacy spelling. Accept only this bounded alias and reject conflicts.
    if max_threads is not None:
        if maximum_threads != 50 and maximum_threads != max_threads:
            raise ValueError("maximum_threads and max_threads disagree")
        maximum_threads = max_threads
    return _call(
        "sync_codex",
        lookback_days=lookback_days,
        maximum_threads=maximum_threads,
        maximum_items=maximum_items,
    )


def attention_queue(context_id: str = "", limit: int = 10) -> str:
    """Rank open loops and tasks without performing them."""
    return _call("attention_queue", context_id=context_id or None, limit=limit)


def context_handoff(context_id: str) -> str:
    """Return a bounded resumption packet for an explicit context."""
    return _call("context_handoff", context_id=context_id)


def context_time_window(context_id: str, relative_date: str = "today") -> str:
    """Resolve today/yesterday/tomorrow in the selected context's timezone."""
    return _call("context_time_window", context_id=context_id, relative_date=relative_date)


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


def view_screen_once(reason: str, context_id: str) -> str:
    """Open the visible selector once, interpret the selection, and retain no pixels."""
    from hermes_attention.screen import understand_screen_once
    return json.dumps(
        understand_screen_once(reason, context_id, PROJECT_PATHS),
        ensure_ascii=False,
        default=str,
    )


def daily_report_draft(report_date: str) -> str:
    """Create a local source-backed draft; publishing is unavailable."""
    return _call("daily_report_draft", report_date=report_date)


def routed_reasoning(route: str, prompt: str, image_data_url: str = "") -> str:
    """Use only an approved non-routine direct-API route."""
    if route not in {"difficult", "vision", "review"}:
        raise ValueError("only difficult, vision, and review escalation routes are exposed")
    service = AttentionService(paths=PROJECT_PATHS)
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


def personal_gmail_search(query: str, limit: int = 10) -> str:
    """Search the isolated personal Gmail account through a bounded read-only API."""
    from hermes_attention.google_direct import PersonalGoogleDirect
    return json.dumps(PersonalGoogleDirect().gmail_search(query, limit), ensure_ascii=False)


def personal_drive_recent(limit: int = 10) -> str:
    """List bounded recent personal Drive metadata through a read-only API."""
    from hermes_attention.google_direct import PersonalGoogleDirect
    return json.dumps(PersonalGoogleDirect().drive_recent(limit), ensure_ascii=False)


def personal_calendar_events(start_time: str, end_time: str, limit: int = 10) -> str:
    """List bounded personal Calendar events through a read-only API."""
    from hermes_attention.google_direct import PersonalGoogleDirect
    return json.dumps(PersonalGoogleDirect().calendar_events(start_time, end_time, limit), ensure_ascii=False)


def work_gmail_search(query: str, limit: int = 10) -> str:
    """Search the isolated work Gmail account through a bounded read-only API."""
    from hermes_attention.google_direct import WorkGoogleDirect
    return json.dumps(WorkGoogleDirect().gmail_search(query, limit), ensure_ascii=False)


def work_drive_recent(limit: int = 10) -> str:
    """List bounded recent work Drive metadata through a read-only API."""
    from hermes_attention.google_direct import WorkGoogleDirect
    return json.dumps(WorkGoogleDirect().drive_recent(limit), ensure_ascii=False)


def work_calendar_events(start_time: str, end_time: str, limit: int = 10) -> str:
    """List bounded work Calendar events through a read-only API."""
    from hermes_attention.google_direct import WorkGoogleDirect
    return json.dumps(WorkGoogleDirect().calendar_events(start_time, end_time, limit), ensure_ascii=False)


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
        "Search source-backed local evidence, optionally constrained to one context. DLOA, worked-today/yesterday, latest-Codex, and project-resumption queries automatically refresh current Codex chats first.",
        {"query": {"type": "string"}, "context_id": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
        ["query"], "🔎",
    ),
    (
        "hermes_attention_sync_codex", sync_codex,
        "Synchronize recent Codex chats now through local stdio using only bounded thread listing/reading methods. Use before a DLOA, worked-today/yesterday answer, or project resumption when freshness matters. No Codex thread or external system is modified.",
        {"lookback_days": {"type": "integer", "minimum": 1, "maximum": 90}, "maximum_threads": {"type": "integer", "minimum": 1, "maximum": 100}, "maximum_items": {"type": "integer", "minimum": 1, "maximum": 5000}},
        [], "🔄",
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
        "hermes_attention_context_time", context_time_window,
        "Resolve today, yesterday, or tomorrow in the requested context before searching any dated evidence. Inside Success uses America/New_York (Miami); Personal uses Asia/Karachi. Mixed or Unknown fails closed. The result includes exact UTC/local bounds and a bounded Slack/Calendar search recipe that avoids broad channel discovery and oversized results.",
        {"context_id": {"type": "string", "enum": ["inside-success", "mitchell", "personal", "mixed", "unknown"]}, "relative_date": {"type": "string", "enum": ["today", "yesterday", "tomorrow"]}},
        ["context_id", "relative_date"], "🕒",
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
        "hermes_attention_view_screen_once", view_screen_once,
        "After the user explicitly asks to inspect the screen, open Apple's visible one-time region selector and describe only the selected pixels with Luna. The user can cancel; no pixels are retained and no computer-control action is available.",
        {"reason": {"type": "string", "minLength": 1, "maxLength": 500}, "context_id": {"type": "string", "enum": ["inside-success", "mitchell", "personal"]}},
        ["reason", "context_id"], "👁️",
    ),
    (
        "hermes_attention_daily_report", daily_report_draft,
        "Refresh recent Codex chats, then draft an evidence-only Inside Success activity report; publishing is unavailable.",
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
    (
        "hermes_attention_personal_gmail_search", personal_gmail_search,
        "Search the isolated personal Gmail account read-only with Gmail query syntax and bounded results.",
        {"query": {"type": "string", "maxLength": 500}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        ["query"], "✉️",
    ),
    (
        "hermes_attention_personal_drive_recent", personal_drive_recent,
        "List bounded recent metadata from the isolated personal Drive account; no create, copy, upload, or download is available.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        [], "🗂️",
    ),
    (
        "hermes_attention_personal_calendar_events", personal_calendar_events,
        "List bounded events from the isolated personal Calendar account; no create, update, delete, or response is available.",
        {"start_time": {"type": "string"}, "end_time": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        ["start_time", "end_time"], "📅",
    ),
    (
        "hermes_attention_work_gmail_search", work_gmail_search,
        "Search the isolated work Gmail account read-only with Gmail query syntax and bounded results.",
        {"query": {"type": "string", "maxLength": 500}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        ["query"], "✉️",
    ),
    (
        "hermes_attention_work_drive_recent", work_drive_recent,
        "List bounded recent metadata from the isolated work Drive account; no create, copy, upload, or download is available.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        [], "🗂️",
    ),
    (
        "hermes_attention_work_calendar_events", work_calendar_events,
        "List bounded events from the isolated work Calendar account; no create, update, delete, or response is available.",
        {"start_time": {"type": "string"}, "end_time": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        ["start_time", "end_time"], "📅",
    ),
)


def register(ctx: Any) -> None:
    """Register the intentionally narrow local tool inventory with Hermes."""
    install_overlay_runtime_bridge(ctx)
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
