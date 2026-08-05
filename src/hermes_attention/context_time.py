"""Deterministic context-local clock and relative-date resolution."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SUPPORTED_RELATIVE_DATES = {"today", "yesterday", "tomorrow"}


def resolve_context_window(
    context_config: dict[str, Any],
    context_id: str,
    relative_date: str = "today",
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve one full local day without borrowing the Mac's timezone.

    Mixed and unknown contexts deliberately fail closed because a single
    relative date can refer to different civil days in different contexts.
    """
    relative = relative_date.strip().lower()
    if relative not in SUPPORTED_RELATIVE_DATES:
        raise ValueError("relative_date must be today, yesterday, or tomorrow")

    context = next(
        (item for item in context_config.get("contexts", []) if item.get("id") == context_id),
        None,
    )
    if context is None:
        raise ValueError(f"unknown context: {context_id}")
    timezone_name = context.get("timezone")
    if not timezone_name:
        raise ValueError("mixed or unknown context requires an explicit date and per-source timezone")
    try:
        zone = ZoneInfo(str(timezone_name))
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"invalid context timezone: {timezone_name}") from exc

    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local_now = instant.astimezone(zone)
    offsets = {"yesterday": -1, "today": 0, "tomorrow": 1}
    local_date: date = local_now.date() + timedelta(days=offsets[relative])
    start_local = datetime.combine(local_date, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=1)

    # The search recipe avoids the expensive failure observed in live use:
    # repeated channel discovery, broad context payloads, and unbounded reads.
    return {
        "context_id": context_id,
        "relative_date": relative,
        "timezone": str(timezone_name),
        "local_now": local_now.isoformat(),
        "local_date": local_date.isoformat(),
        "start_local": start_local.isoformat(),
        "end_local_exclusive": end_local.isoformat(),
        "start_utc": start_local.astimezone(UTC).isoformat(),
        "end_utc_exclusive": end_local.astimezone(UTC).isoformat(),
        "start_unix": str(int(start_local.timestamp())),
        "end_unix_exclusive": str(int(end_local.timestamp())),
        "search_guidance": {
            "slack": {
                "use_one_bounded_search_first": True,
                "after": str(int(start_local.timestamp())),
                "before": str(int(end_local.timestamp()) - 1),
                "limit": 20,
                "response_format": "concise",
                "include_context": False,
                "sort": "timestamp",
                "sort_dir": "desc",
                "avoid_channel_enumeration": True,
                "read_only_relevant_threads_after_search": True,
            },
            "calendar": {
                "start_time": start_local.isoformat(),
                "end_time": end_local.isoformat(),
                "limit": 20,
            },
        },
    }
