#!/usr/bin/env python3
"""Run bounded real-data acceptance without printing or committing private answers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.acceptance import REAL_CASES, RealAcceptanceRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--private-dir", type=Path, default=ROOT / "runtime-data/acceptance-private/prompt4")
    parser.add_argument("--summary", type=Path, default=ROOT / "runtime-data/acceptance-prompt4-summary.json")
    parser.add_argument("--case", action="append", choices=tuple(item.case_id for item in REAL_CASES))
    arguments = parser.parse_args()
    selected = tuple(item for item in REAL_CASES if not arguments.case or item.case_id in arguments.case)
    result = RealAcceptanceRunner(ROOT, arguments.private_dir).run(start_date=arguments.start_date, end_date=arguments.end_date, cases=selected)
    arguments.summary.parent.mkdir(parents=True, exist_ok=True)
    arguments.summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(arguments.summary, 0o600)
    print(json.dumps({
        "accepted": result["accepted"], "total": result["total"],
        "latency_ms_total": result["latency_ms_total"],
        "estimated_cost_usd": result["estimated_cost_usd"],
        "summary": str(arguments.summary), "private_content_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
