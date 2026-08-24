"""Import strict-valid private Zoom acceptance evidence without printing content."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from .acceptance import REAL_CASES, summarize_private_result
from .domain import ConfidenceState, ContextLabel, EvidenceItem, Provenance
from .service import AttentionService
from .work_ledger import LedgerEntryInput


ZOOM_CASE = next(case for case in REAL_CASES if case.case_id == "zoom_recent_meeting")


def _private_path(path: Path, private_root: Path) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    root = private_root.expanduser().resolve(strict=True)
    if resolved != root and root not in resolved.parents:
        raise PermissionError("Zoom acceptance input must remain under the private acceptance root")
    if not resolved.is_file():
        raise ValueError("Zoom acceptance input must be a regular file")
    return resolved


def _safe_zoom_uri(reference: str) -> str | None:
    parsed = urlparse(reference)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (host == "zoom.us" or host.endswith(".zoom.us")):
        return reference
    return None


def import_zoom_acceptance(
    service: AttentionService,
    response_path: Path,
    *,
    private_root: Path,
) -> dict[str, Any]:
    """Promote a previously accepted read-only Zoom result into immutable evidence.

    The private response remains owner-only. Public output contains counts and
    hashes only; provider references are stored as hashes unless they are HTTPS
    Zoom URLs. The operation is deterministic and idempotent.
    """
    path = _private_path(response_path, private_root)
    response = path.read_text(encoding="utf-8")
    summary = summarize_private_result(ZOOM_CASE, response, {}, 0, 0)
    if not summary["accepted"] or summary["reported_leakage"]:
        raise ValueError("Zoom acceptance result is not strict-valid")
    payload = json.loads(response)
    if payload.get("writes_disabled") is not True:
        raise PermissionError("Zoom acceptance result did not prove writes disabled")

    sources = payload.get("sources")
    claims = payload.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise ValueError("Zoom acceptance result is malformed")
    source_refs = [str(source.get("ref") or "") for source in sources if isinstance(source, dict)]
    if not source_refs or len(source_refs) != len(set(source_refs)) or any(not ref for ref in source_refs):
        raise ValueError("Zoom acceptance source references must be present and unique")

    retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    response_hash = sha256(response.encode("utf-8")).hexdigest()
    evidence_ids: list[str] = []
    source_dates: list[str] = []
    inserted = 0

    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Zoom acceptance source must be an object")
        if source.get("system") != "zoom_readonly":
            raise PermissionError("Zoom acceptance may import Zoom read-only sources only")
        connection = str(source.get("connection_id") or "")
        if not connection.startswith("zoom_readonly:"):
            raise PermissionError("Zoom acceptance source is not from the reviewed connection")
        if source.get("context") != "inside-success":
            raise PermissionError("Zoom acceptance source must remain in Inside Success")
        reference = str(source["ref"])
        matching_claims = [
            str(claim.get("claim") or "").strip()
            for claim in claims
            if isinstance(claim, dict)
            and reference in claim.get("source_refs", [])
            and claim.get("label_state") == "confirmed"
            and isinstance(claim.get("confidence"), (int, float))
            and float(claim["confidence"]) >= 0.9
        ]
        if not matching_claims or any(not claim for claim in matching_claims):
            raise ValueError("Every imported Zoom source requires a confirmed cited claim")
        source_date = str(source.get("date") or "")
        try:
            datetime.fromisoformat(source_date)
        except ValueError as exc:
            raise ValueError("Zoom acceptance source date must be ISO formatted") from exc
        source_dates.append(source_date)
        reference_hash = sha256(reference.encode("utf-8")).hexdigest()
        evidence_id = f"zoom-accepted-{reference_hash[:32]}"
        evidence_ids.append(evidence_id)
        item = EvidenceItem(
            evidence_id=evidence_id,
            title=f"Authorized Zoom meeting evidence — {source_date}",
            content="\n".join(matching_claims),
            provenance=Provenance(
                source_system="zoom",
                connection_id="zoom_readonly",
                source_id=reference_hash,
                source_timestamp=f"{source_date}T00:00:00+00:00",
                retrieved_at=retrieved_at,
                account_id="work",
                workspace="Inside Success",
                container=connection.split(":", 1)[1],
                uri=_safe_zoom_uri(reference),
                permission_ref="zoom-readonly-accepted-result",
                metadata={
                    "acceptance_case": ZOOM_CASE.case_id,
                    "acceptance_response_sha256": response_hash,
                    "provider_reference_sha256": reference_hash,
                    "provider_connection": connection,
                },
            ),
            contexts=(ContextLabel(
                context_id="inside-success",
                confidence=1.0,
                reason="strict-valid read-only Zoom acceptance evidence",
                classifier_version="zoom-acceptance-import-v1",
            ),),
            sensitivity="private",
            confidence_state=ConfidenceState.CONFIRMED,
        )
        inserted += int(service.store.add_evidence(item))

    occurred_at = f"{max(source_dates)}T00:00:00+00:00"
    ledger_id, ledger_created = service.ledger.record(LedgerEntryInput(
        kind="meeting",
        occurred_at_utc=occurred_at,
        context_id="inside-success",
        summary="Authorized Zoom meeting evidence is available for reviewed local follow-up",
        evidence_ids=tuple(evidence_ids),
        actor_state="confirmed",
        confidence_state="confirmed",
    ))
    service.store.audit("acceptance", "zoom.accepted_evidence.import", "inside-success", "success", {
        "response_sha256": response_hash,
        "source_count": len(evidence_ids),
        "inserted_count": inserted,
        "ledger_created": ledger_created,
        "writes_disabled": True,
        "private_content_printed": False,
    })
    return {
        "ok": True,
        "source_count": len(evidence_ids),
        "inserted_count": inserted,
        "ledger_id": ledger_id,
        "ledger_created": ledger_created,
        "response_sha256": response_hash,
        "external_write": False,
        "private_content_printed": False,
    }
