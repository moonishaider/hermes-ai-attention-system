"""Read-only GitHub evidence normalization and tool-inventory validation."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from .domain import ConfidenceState, EvidenceItem, Provenance
from .routing import ContextRouter
from .security import detect_prompt_injection, redact_secrets


GITHUB_WRITE_TOKENS = {
    "create",
    "update",
    "delete",
    "merge",
    "push",
    "fork",
    "archive",
    "add",
    "remove",
    "rerun",
    "enable",
    "disable",
}


def assert_read_only_tool_inventory(tools: list[str]) -> None:
    unexpected = []
    for tool in tools:
        tokens = set(tool.casefold().replace("-", "_").split("_"))
        if tokens & GITHUB_WRITE_TOKENS:
            unexpected.append(tool)
    if unexpected:
        raise PermissionError(f"GitHub write/admin tools exposed: {', '.join(sorted(unexpected))}")


def normalize_github_item(
    payload: dict[str, Any],
    *,
    connection_id: str,
    owner: str,
    repository: str,
    object_type: str,
    router: ContextRouter,
) -> EvidenceItem:
    native_id = str(payload.get("id") or payload.get("sha") or payload.get("number") or payload.get("path"))
    if not native_id or native_id == "None":
        raise ValueError("GitHub evidence requires an immutable object identifier")
    metadata = {
        "owner": owner,
        "repository": repository,
        "visibility": payload.get("visibility"),
        "object_type": object_type,
        "branch": payload.get("branch") or payload.get("ref"),
        "commit_sha": payload.get("sha") or payload.get("commit_sha"),
        "path": payload.get("path"),
        "line_start": payload.get("line_start"),
        "line_end": payload.get("line_end"),
        "number": payload.get("number"),
    }
    content, _ = redact_secrets(str(payload.get("content") or payload.get("body") or payload.get("message") or payload.get("title") or ""))
    timestamp = str(payload.get("updated_at") or payload.get("created_at") or datetime.now(UTC).isoformat())
    revision = str(payload.get("sha") or payload.get("updated_at") or native_id)
    provenance = Provenance(
        source_system="github",
        connection_id=connection_id,
        source_id=native_id,
        source_timestamp=timestamp,
        retrieved_at=datetime.now(UTC).isoformat(),
        account_id=owner,
        workspace=owner,
        container=repository,
        author=str(payload.get("author") or payload.get("actor") or "unknown"),
        uri=payload.get("url") or payload.get("html_url"),
        revision=revision,
        permission_ref="github-readonly",
        metadata=metadata,
    )
    return EvidenceItem(
        evidence_id=f"github:{sha256(f'{owner}/{repository}/{object_type}/{native_id}/{revision}'.encode()).hexdigest()}",
        title=str(payload.get("title") or payload.get("path") or f"{owner}/{repository} {object_type}"),
        content=content,
        provenance=provenance,
        contexts=router.classify(provenance),
        confidence_state=ConfidenceState.UNCERTAIN if detect_prompt_injection(content) else ConfidenceState.INFERRED,
    )
