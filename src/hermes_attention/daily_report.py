"""Fixed-destination configuration and payload guards for the company DLOA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .config import ConfigurationError, load_json


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BROAD_MENTIONS = ("<!channel>", "<!here>", "@channel", "@here", "@everyone")


@dataclass(frozen=True, slots=True)
class DailyReportLock:
    action_type: str
    context_id: str
    workspace_id: str
    workspace_name: str
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
