#!/usr/bin/env python3
"""Compose strict-valid private acceptance results without new connector calls."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.acceptance import REAL_CASES, compose_accepted_results  # noqa: E402


def _below(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, choices=("context_switch_handoff", "commitment_contradiction"))
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--input-case", action="append", required=True, choices=tuple(item.case_id for item in REAL_CASES))
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    arguments = parser.parse_args()
    if len(arguments.input) != len(arguments.input_case):
        parser.error("--input and --input-case counts must match")
    private_root = ROOT / "runtime-data/acceptance-private"
    if any(not path.is_file() or not _below(path, private_root) for path in arguments.input):
        parser.error("every input must be an existing file below runtime-data/acceptance-private")
    if not _below(arguments.private_output, private_root):
        parser.error("private output must be below runtime-data/acceptance-private")
    if not _below(arguments.summary, ROOT / "runtime-data"):
        parser.error("summary must be below runtime-data")
    if arguments.private_output.exists() or arguments.summary.exists():
        parser.error("outputs already exist; private acceptance artifacts are never overwritten")
    cases = {item.case_id: item for item in REAL_CASES}
    inputs = tuple(
        (cases[case_id], path.resolve().read_text(encoding="utf-8"))
        for case_id, path in zip(arguments.input_case, arguments.input, strict=True)
    )
    response, summary = compose_accepted_results(cases[arguments.case], inputs)
    for path, content in (
        (arguments.private_output, response + "\n"),
        (arguments.summary, json.dumps(summary, indent=2, sort_keys=True) + "\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o600)
    print(json.dumps({
        "accepted": summary["accepted"],
        "case_id": summary["case_id"],
        "claim_count": summary["claim_count"],
        "source_count": summary["source_count"],
        "private_content_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
