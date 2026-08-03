#!/usr/bin/env python3
"""Create an owner-only exact Slack preview; this script has no sender."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.actions import ActionController  # noqa: E402
from hermes_attention.daily_report import load_daily_report_lock, validate_daily_report_payload  # noqa: E402
from hermes_attention.domain import RiskClass  # noqa: E402
from hermes_attention.policy import PolicyEngine  # noqa: E402
from hermes_attention.storage import Store  # noqa: E402


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--evidence-id", action="append", default=[])
    arguments = parser.parse_args()

    runtime = ROOT / "runtime-data"
    text_path = arguments.text_file.resolve()
    if not _within(text_path, runtime) or not text_path.is_file():
        parser.error("text file must be an existing file below runtime-data")

    lock = load_daily_report_lock(ROOT / "config/actions/inside_success_daily_report.json")
    payload = {"text": text_path.read_text(encoding="utf-8"), "report_date": arguments.report_date}
    validate_daily_report_payload(payload, lock)

    policy = PolicyEngine(external_writes_enabled=False, kill_switch=True)
    database = runtime / "hermes_attention.sqlite3"
    with Store(database) as store:
        proposal = ActionController(store, policy).propose(
            action_type=lock.action_type,
            context_id=lock.context_id,
            risk_class=RiskClass.A2,
            target={"workspace_id": lock.workspace_id, "channel_id": lock.channel_id},
            payload=payload,
            evidence_ids=tuple(arguments.evidence_id),
            ttl_minutes=lock.approval_expiry_minutes,
        )

    preview_dir = runtime / "action-previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{proposal.proposal_id}.json"
    preview_path.write_text(json.dumps(asdict(proposal), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(preview_path, 0o600)
    print(json.dumps({
        "created": True,
        "execution_performed": False,
        "kill_switch_active": True,
        "generic_send_available": False,
        "workspace_id": lock.workspace_id,
        "channel_id": lock.channel_id,
        "channel_name": lock.channel_name,
        "preview_hash": proposal.preview_hash,
        "expires_at": proposal.expires_at,
        "private_preview_path": str(preview_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
