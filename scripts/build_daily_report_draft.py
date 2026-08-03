#!/usr/bin/env python3
"""Build a private DLOA draft from a previously accepted real-data result."""

from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.daily_report import load_daily_report_lock, validate_daily_report_payload  # noqa: E402


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _json_object(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("accepted result does not contain a JSON object")
    value = json.loads(raw[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("accepted result must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-result", required=True, type=Path)
    parser.add_argument("--report-date", required=True)
    arguments = parser.parse_args()

    runtime = ROOT / "runtime-data"
    source_path = arguments.accepted_result.resolve()
    if not _within(source_path, runtime / "acceptance-private") or not source_path.is_file():
        parser.error("accepted result must be an existing file below runtime-data/acceptance-private")
    try:
        report_date = date.fromisoformat(arguments.report_date)
    except ValueError as exc:
        parser.error(f"report date must use YYYY-MM-DD: {exc}")

    result = _json_object(source_path.read_text(encoding="utf-8"))
    if result.get("success") is not True or result.get("writes_disabled") is not True:
        parser.error("source acceptance was not successful with writes disabled")
    if result.get("leakage_detected") is not False:
        parser.error("source acceptance did not pass its leakage check")

    sources = result.get("sources")
    claims = result.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        parser.error("accepted result has no structured sources/claims")
    source_by_ref = {
        item.get("ref"): item
        for item in sources
        if isinstance(item, dict) and isinstance(item.get("ref"), str)
    }
    accepted_claims: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("label_state") not in {"confirmed", "inferred"}:
            continue
        text = claim.get("claim")
        refs = claim.get("source_refs")
        if not isinstance(text, str) or not text.strip() or not isinstance(refs, list) or not refs:
            continue
        evidence = [source_by_ref.get(ref) for ref in refs]
        if any(item is None or item.get("context") != "inside-success" for item in evidence):
            continue
        accepted_claims.append({"text": text.strip().lstrip("•- "), "refs": refs, "label_state": claim["label_state"]})
    if not accepted_claims:
        parser.error("no source-backed Inside Success claims are safe to draft")

    human_date = f"{report_date.day} {report_date.strftime('%B %Y')}"
    text = "DLOA – " + human_date + "\n" + "\n".join(f"• {item['text']}" for item in accepted_claims) + "\n"
    lock = load_daily_report_lock(ROOT / "config/actions/inside_success_daily_report.json")
    validate_daily_report_payload({"text": text, "report_date": arguments.report_date}, lock)

    output_dir = runtime / "daily-reports" / arguments.report_date
    output_dir.mkdir(parents=True, exist_ok=True)
    draft_path = output_dir / "draft.txt"
    manifest_path = output_dir / "evidence-manifest.json"
    if draft_path.exists() or manifest_path.exists():
        parser.error("private draft already exists; it will not be overwritten")
    draft_path.write_text(text, encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "report_date": arguments.report_date,
        "source_result_sha256": sha256(source_path.read_bytes()).hexdigest(),
        "claim_count": len(accepted_claims),
        "confirmed_count": sum(item["label_state"] == "confirmed" for item in accepted_claims),
        "inferred_count": sum(item["label_state"] == "inferred" for item in accepted_claims),
        "source_ref_hashes": sorted({sha256(ref.encode("utf-8")).hexdigest() for item in accepted_claims for ref in item["refs"]}),
        "raw_source_content_stored": False,
        "slack_send_performed": False,
    }, indent=2) + "\n", encoding="utf-8")
    os.chmod(draft_path, 0o600)
    os.chmod(manifest_path, 0o600)
    print(json.dumps({
        "created": True,
        "report_date": arguments.report_date,
        "claim_count": len(accepted_claims),
        "draft_path": str(draft_path),
        "manifest_path": str(manifest_path),
        "slack_send_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
