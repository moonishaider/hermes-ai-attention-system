"""Credential-safe startup health view for daily Hermes use."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from .history import CodexHistoryBridge
from .secrets import configured_keys


def _token_health(name: str, token_root: Path, now: float) -> dict[str, Any]:
    path = token_root / f"{name}.json"
    if not path.is_file():
        return {"state": "authorization-required", "expires_at": None, "refreshable": False}
    try:
        token = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "invalid-local-token-record", "expires_at": None, "refreshable": False}
    expiry = float(token.get("expires_at") or 0)
    refresh_expiry = float(token.get("refresh_token_expires_at") or 0)
    refreshable = bool(token.get("refresh_token"))
    remaining = int(expiry - now) if expiry else None
    refresh_remaining = int(refresh_expiry - now) if refresh_expiry else None
    if refreshable and refresh_remaining is not None and refresh_remaining <= 0:
        state = "reauthorization-required"
    elif refreshable and refresh_remaining is not None and refresh_remaining <= 86400:
        state = "refresh-token-expires-soon"
    elif remaining is None:
        state = "present-expiry-unknown"
    elif remaining <= 0 and refreshable:
        state = "expired-refresh-available"
    elif remaining <= 0:
        state = "reauthorization-required"
    elif remaining <= 3600 and refreshable:
        state = "ready-refreshable"
    elif remaining <= 3600:
        state = "expires-soon"
    else:
        state = "ready"
    return {
        "state": state,
        "expires_at": datetime.fromtimestamp(expiry, UTC).isoformat() if expiry else None,
        "seconds_remaining": remaining,
        "refreshable": refreshable,
        "refresh_token_expires_at": datetime.fromtimestamp(refresh_expiry, UTC).isoformat() if refresh_expiry else None,
        "refresh_token_seconds_remaining": refresh_remaining,
    }


def _aggregate_token_health(prefix: str, token_root: Path, now: float) -> dict[str, Any]:
    names = sorted(path.name.removesuffix(".json") for path in token_root.glob(f"{prefix}_*.json") if not path.name.endswith((".client.json", ".meta.json")))
    if not names:
        return {"state": "authorization-required", "resources": {}}
    resources = {name.removeprefix(prefix + "_"): _token_health(name, token_root, now) for name in names}
    states = {item["state"] for item in resources.values()}
    priority = (
        "invalid-local-token-record", "reauthorization-required", "authorization-required",
        "refresh-token-expires-soon", "expires-soon", "expired-refresh-available", "present-expiry-unknown", "ready-refreshable", "ready",
    )
    state = next((candidate for candidate in priority if candidate in states), "unknown")
    return {"state": state, "resources": resources}


def startup_health(service: Any) -> dict[str, Any]:
    """Return operational state without token values, source content, or prompts."""
    now = datetime.now(UTC)
    token_root = Path.home() / ".hermes" / "mcp-tokens"
    chatgpt_records = int(service.store.connection.execute(
        "SELECT COUNT(*) FROM evidence WHERE evidence_id LIKE 'chatgpt:%' AND tombstoned_at IS NULL"
    ).fetchone()[0])
    gemini_records = int(service.store.connection.execute(
        "SELECT COUNT(*) FROM evidence WHERE evidence_id LIKE 'gemini:%' AND tombstoned_at IS NULL"
    ).fetchone()[0])
    connectors: dict[str, Any] = {}
    for name, record in sorted(service.integrations.connections.items()):
        base = {
            "mode": record["mode"],
            "configured_enabled": bool(record.get("enabled")),
            "account_boundary": record.get("account_boundary") or record.get("owner_boundary") or "local",
        }
        if name.startswith("google_"):
            prefix = name.removesuffix("_readonly")
            base.update(_aggregate_token_health(prefix, token_root, now.timestamp()))
        elif name.startswith("slack_"):
            base.update(_token_health(name, token_root, now.timestamp()))
        elif name.startswith("github_"):
            secret_name = "MCP_GITHUB_PERSONAL_READONLY_API_KEY" if "personal" in name else "MCP_GITHUB_INSIDE_SUCCESS_READONLY_API_KEY"
            base["state"] = "configured-live-smoked" if configured_keys().get(secret_name) else "credential-required"
        elif name == "zoom_readonly":
            if not record.get("enabled"):
                base["state"] = "oauth-required-disabled"
            else:
                base.update(_token_health(name, token_root, now.timestamp()))
        elif name == "chatgpt_export_backfill":
            base["state"] = "imported" if chatgpt_records else "awaiting-user-selected-official-export"
            base["records"] = chatgpt_records
        elif name == "gemini_export_backfill":
            base["state"] = "imported" if gemini_records else "awaiting-user-selected-official-takeout"
            base["records"] = gemini_records
        else:
            base["state"] = "local-ready" if record.get("enabled") else "disabled"
        connectors[name] = base

    preview = CodexHistoryBridge(service.store, service.router).preview(start_date="2026-03-01")
    checkpoint_rows = service.store.connection.execute(
        "SELECT source_id,cursor,updated_at FROM checkpoints WHERE source_id LIKE 'codex:%'"
    ).fetchall()
    checkpointed_lines = sum(int(row["cursor"]) for row in checkpoint_rows if str(row["cursor"]).isdigit())
    last_checkpoint = max((str(row["updated_at"]) for row in checkpoint_rows), default=None)
    live_codex = service.status()["codex_sync"]
    routes = {
        route_id: {"provider": route.provider, "model": route.model, "purpose": route.purpose}
        for route_id, route in service.models.routes.items()
    }
    return {
        "checked_at": now.isoformat(),
        "project_root": str(service.paths.root),
        "launch_mode": "trusted-project-only",
        "models": {
            "default": service.models.default_route,
            "routes": routes,
            "builder_only": "gpt-5.6-sol",
            "budget": service.models.budget_status(),
        },
        "connectors": connectors,
        "codex_ingestion": {
            "start_date": preview["start_date"],
            "candidate_files": preview["files"],
            "candidate_bytes": preview["bytes"],
            "checkpoint_files": len(checkpoint_rows),
            "checkpointed_lines": checkpointed_lines,
            "last_checkpoint_at": last_checkpoint,
            "pending_lines": "not-counted-at-startup-to-avoid-scanning-6GB-history",
            "live_sync": live_codex,
            "read_methods": ["thread/list", "thread/turns/list"],
            "thread_mutations": False,
        },
        "chatgpt": {
            "state": "imported" if chatgpt_records else "awaiting-user-selected-official-export",
            "records": chatgpt_records,
            "continuous_sync": False,
        },
        "gemini": {
            "state": "imported" if gemini_records else "awaiting-user-selected-official-takeout",
            "records": gemini_records,
            "continuous_sync": False,
            "binary_attachments_ingested": False,
        },
        "zoom": {"state": connectors.get("zoom_readonly", {}).get("state", "disabled")},
        "external_actions": {
            "enabled": service.policy.external_writes_enabled,
            "kill_switch": service.policy.kill_switch,
            "generic_slack_send_exposed": False,
        },
        "capability_boundaries": {
            "public_web": "read-only-search-fetch",
            "logged_in_browser": False,
            "computer_use": False,
            "continuous_screen_capture": False,
            "persistent_service": False,
        },
        "warnings": [
            name for name, value in connectors.items()
            if value.get("state") in {"reauthorization-required", "refresh-token-expires-soon", "expires-soon", "credential-required", "oauth-required-disabled"}
        ],
        "secrets_printed": False,
        "private_content_printed": False,
    }
