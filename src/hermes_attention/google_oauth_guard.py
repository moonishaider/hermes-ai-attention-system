"""Fail-closed OAuth scope selection for Google Workspace MCP servers."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse


APPROVED_SCOPES = {
    "gmailmcp.googleapis.com": ("https://www.googleapis.com/auth/gmail.readonly",),
    "drivemcp.googleapis.com": ("https://www.googleapis.com/auth/drive.readonly",),
    "calendarmcp.googleapis.com": (
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
    ),
}


def _resource_host(protected_resource_metadata: object | None) -> str:
    resource = getattr(protected_resource_metadata, "resource", "") or ""
    return (urlparse(str(resource)).hostname or "").lower()


def select_google_scopes(
    protected_resource_metadata: object | None,
) -> str | None:
    """Return the immutable allowlist for a recognized Google MCP resource."""
    scopes = APPROVED_SCOPES.get(_resource_host(protected_resource_metadata))
    return " ".join(scopes) if scopes else None


def install_google_oauth_scope_guard() -> bool:
    """Patch MCP SDK scope discovery so Google metadata cannot widen access."""
    try:
        from mcp.client.auth import oauth2
    except ImportError:
        return False

    current: Callable[..., str | None] = oauth2.get_client_metadata_scopes
    if getattr(current, "_hermes_attention_google_guard", False):
        return True

    def guarded_scope_selection(
        www_authenticate_scope: str | None,
        protected_resource_metadata: object | None,
        authorization_server_metadata: object | None = None,
    ) -> str | None:
        approved = select_google_scopes(protected_resource_metadata)
        if approved is not None:
            return approved
        return current(
            www_authenticate_scope,
            protected_resource_metadata,
            authorization_server_metadata,
        )

    guarded_scope_selection._hermes_attention_google_guard = True  # type: ignore[attr-defined]
    oauth2.get_client_metadata_scopes = guarded_scope_selection
    return True


def validated_read_probe_blocks(result: object) -> list[object]:
    """Return successful MCP content blocks and fail closed on protocol errors."""
    if bool(getattr(result, "isError", False)):
        raise RuntimeError("Google MCP read probe returned a provider error")
    blocks = list(getattr(result, "content", None) or [])
    if not blocks:
        raise RuntimeError("Google MCP read probe returned no content")
    return blocks
