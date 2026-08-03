#!/usr/bin/env python3
"""Normalize validated company acceptance evidence into an exact source table."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.acceptance import REAL_CASES, summarize_private_result  # noqa: E402
from hermes_attention.daily_report import load_daily_report_lock, normalize_inside_success_result  # noqa: E402


def _below(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--case", default="worked_today", choices=("inside_success_daily_brief", "worked_today", "daily_report_draft"))
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    arguments = parser.parse_args()
    private_root = ROOT / "runtime-data/acceptance-private"
    if not arguments.input.is_file() or not _below(arguments.input, private_root):
        parser.error("input must be an existing file below runtime-data/acceptance-private")
    if not _below(arguments.private_output, private_root):
        parser.error("private output must be below runtime-data/acceptance-private")
    if not _below(arguments.summary, ROOT / "runtime-data"):
        parser.error("summary must be below runtime-data")
    if arguments.private_output.exists() or arguments.summary.exists():
        parser.error("outputs already exist; private acceptance artifacts are never overwritten")
    raw = arguments.input.resolve().read_text(encoding="utf-8")
    payload, _ = json.JSONDecoder().raw_decode(raw.lstrip())
    if not isinstance(payload, dict):
        raise ValueError("input response does not start with a JSON object")
    lock = load_daily_report_lock(ROOT / "config/actions/inside_success_daily_report.json")
    normalized = normalize_inside_success_result(payload, lock, case_id=arguments.case)
    response = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    case = next(item for item in REAL_CASES if item.case_id == arguments.case)
    summary = summarize_private_result(case, response, {"provider": "local", "model": "validated-source-normalizer"}, 0, 0)
    if not summary["accepted"]:
        raise ValueError("normalized result failed strict validation")
    for path, content in (
        (arguments.private_output, response + "\n"),
        (arguments.summary, json.dumps(summary, indent=2, sort_keys=True) + "\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o600)
    print(json.dumps({
        "accepted": True, "claim_count": summary["claim_count"],
        "source_count": summary["source_count"], "private_content_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
