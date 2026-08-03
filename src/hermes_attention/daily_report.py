"""Fixed-destination configuration and payload guards for the company DLOA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from .config import ConfigurationError, load_json


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BROAD_MENTIONS = ("<!channel>", "<!here>", "@channel", "@here", "@everyone")
_SLACK_ARCHIVE_PATH = re.compile(r"^/archives/[CDG][A-Z0-9]+/p\d+$")
_UNUSABLE_REFERENCE_MARKERS = ("total_count=0", "no hits", "permission denied", "unavailable")


@dataclass(frozen=True, slots=True)
class DailyReportLock:
    action_type: str
    context_id: str
    workspace_id: str
    workspace_name: str
    slack_workspace_domain: str
    channel_id: str
    channel_name: str
    author_user_id: str
    author_name: str
    approval_expiry_minutes: int
    message_max_characters: int


def load_daily_report_lock(path: Path) -> DailyReportLock:
    value = load_json(path)
    required: dict[str, type] = {
        "action_type": str,
        "context_id": str,
        "workspace_id": str,
        "workspace_name": str,
        "slack_workspace_domain": str,
        "channel_id": str,
        "channel_name": str,
        "author_user_id": str,
        "author_name": str,
        "approval_expiry_minutes": int,
        "message_max_characters": int,
    }
    for key, expected_type in required.items():
        if type(value.get(key)) is not expected_type:
            raise ConfigurationError(f"daily report lock has invalid {key}")
    if value.get("schema_version") != 1:
        raise ConfigurationError("daily report lock schema_version must be 1")
    if value["action_type"] != "publish_inside_success_daily_update":
        raise ConfigurationError("daily report lock permits only the Inside Success daily update")
    if value["context_id"] != "inside-success":
        raise ConfigurationError("daily report lock must use the inside-success context")
    if value.get("execution_mode") != "supervised-preview":
        raise ConfigurationError("daily report execution must remain supervised-preview")
    if value.get("generic_send_exposed") is not False:
        raise ConfigurationError("generic Slack sending must remain unexposed")
    if not value["workspace_id"].startswith("T") or not value["channel_id"].startswith("C"):
        raise ConfigurationError("daily report workspace/channel IDs are malformed")
    if not value["slack_workspace_domain"].endswith(".slack.com") or "/" in value["slack_workspace_domain"]:
        raise ConfigurationError("daily report Slack workspace domain is malformed")
    if not 1 <= value["approval_expiry_minutes"] <= 60:
        raise ConfigurationError("daily report approval expiry must be between 1 and 60 minutes")
    if not 1 <= value["message_max_characters"] <= 8000:
        raise ConfigurationError("daily report message limit must be between 1 and 8000 characters")
    return DailyReportLock(**{key: value[key] for key in required})


def validate_daily_report_payload(payload: dict[str, Any], lock: DailyReportLock) -> str:
    if not isinstance(payload, dict) or not set(payload) <= {"text", "report_date"}:
        raise ValueError("daily report payload permits only text and report_date")
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("daily report text is required")
    if len(text) > lock.message_max_characters:
        raise ValueError("daily report exceeds the configured character limit")
    if any(mention.casefold() in text.casefold() for mention in _BROAD_MENTIONS):
        raise ValueError("daily report cannot contain a broad Slack mention")
    report_date = payload.get("report_date")
    if report_date is not None and (not isinstance(report_date, str) or not _DATE.fullmatch(report_date)):
        raise ValueError("daily report date must use YYYY-MM-DD")
    return text


def resolve_inside_success_source(
    ref: str,
    source_by_ref: dict[str, dict[str, Any]],
    *,
    slack_workspace_domain: str,
) -> dict[str, Any] | None:
    existing = source_by_ref.get(ref)
    if existing is not None:
        if existing.get("context") != "inside-success":
            return None
        lowered = ref.casefold()
        if any(marker in lowered for marker in _UNUSABLE_REFERENCE_MARKERS):
            return None
        return existing
    try:
        parsed = urlsplit(ref)
    except ValueError:
        return None
    if (
        parsed.scheme == "https"
        and parsed.hostname == slack_workspace_domain
        and not parsed.query
        and not parsed.fragment
        and _SLACK_ARCHIVE_PATH.fullmatch(parsed.path)
    ):
        return {
            "system": "slack",
            "connection_id": "slack_inside_success_readonly",
            "ref": ref,
            "context": "inside-success",
            "derived_from_validated_permalink": True,
        }
    return None


def select_dloa_claims(result: dict[str, Any], lock: DailyReportLock) -> tuple[list[dict[str, Any]], int]:
    sources = result.get("sources")
    claims = result.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise ValueError("accepted result has no structured sources/claims")
    source_by_ref = {
        item.get("ref"): item
        for item in sources
        if isinstance(item, dict) and isinstance(item.get("ref"), str)
    }
    accepted: list[dict[str, Any]] = []
    derived_count = 0
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("label_state") not in {"confirmed", "inferred"}:
            continue
        text = claim.get("claim")
        refs = claim.get("source_refs")
        if not isinstance(text, str) or not text.strip() or not isinstance(refs, list) or not refs:
            continue
        evidence = [
            resolve_inside_success_source(
                ref,
                source_by_ref,
                slack_workspace_domain=lock.slack_workspace_domain,
            )
            for ref in refs
            if isinstance(ref, str)
        ]
        if len(evidence) != len(refs) or any(item is None for item in evidence):
            continue
        derived_count += sum(bool(item.get("derived_from_validated_permalink")) for item in evidence if item)
        accepted.append({
            "text": text.strip().lstrip("•- "),
            "refs": refs,
            "label_state": claim["label_state"],
            "source_systems": sorted({str(item.get("system")) for item in evidence if item}),
        })
    return accepted, derived_count


def normalize_inside_success_result(result: dict[str, Any], lock: DailyReportLock, *, case_id: str) -> dict[str, Any]:
    """Return a strict source table containing only DLOA-eligible company claims."""
    sources = result.get("sources")
    claims = result.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise ValueError("accepted result has no structured sources/claims")
    source_by_ref = {
        item.get("ref"): item
        for item in sources
        if isinstance(item, dict) and isinstance(item.get("ref"), str)
    }
    normalized_claims: list[dict[str, Any]] = []
    normalized_sources: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("label_state") not in {"confirmed", "inferred"}:
            continue
        refs = claim.get("source_refs")
        if not isinstance(claim.get("claim"), str) or not isinstance(refs, list) or not refs:
            continue
        resolved = [
            resolve_inside_success_source(ref, source_by_ref, slack_workspace_domain=lock.slack_workspace_domain)
            for ref in refs if isinstance(ref, str)
        ]
        if len(resolved) != len(refs) or any(item is None for item in resolved):
            continue
        for item in resolved:
            assert item is not None
            reference = str(item["ref"])
            if reference in normalized_sources and normalized_sources[reference] != item:
                raise ValueError("conflicting normalized source metadata")
            normalized_sources[reference] = item
        normalized_claims.append({
            "claim": claim["claim"],
            "source_refs": list(refs),
            "confidence": claim.get("confidence", 0.5),
            "label_state": claim["label_state"],
        })
    if not normalized_claims:
        raise ValueError("no strict-valid Inside Success claims remain")
    return {
        "case_id": case_id,
        "status_checked": True,
        "writes_disabled": True,
        "success": True,
        "answer": "Private normalized Inside Success evidence; raw claims remain in the owner-only artifact.",
        "claims": normalized_claims,
        "sources": [normalized_sources[ref] for ref in sorted(normalized_sources)],
        "leakage_detected": False,
        "failure_reason": None,
    }
