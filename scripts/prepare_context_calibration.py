#!/usr/bin/env python3
"""Create one private, bounded context-calibration packet without changing evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.calibration import prepare_context_calibration  # noqa: E402
from hermes_attention.storage import Store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-source", type=int, default=6)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    private_root = (ROOT / "runtime-data/calibration-private").resolve()
    try:
        output.relative_to(private_root)
    except ValueError:
        parser.error("output must be below runtime-data/calibration-private")
    if output.exists():
        parser.error("calibration packet already exists; it will not be overwritten")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output.parent, 0o700)
    with Store(ROOT / "runtime-data/hermes_attention.sqlite3") as store:
        packet = prepare_context_calibration(store, per_source=arguments.per_source)
    output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    counts: dict[str, int] = {}
    for item in packet["items"]:
        counts[item["source_system"]] = counts.get(item["source_system"], 0) + 1
    print(json.dumps({
        "created": True,
        "private_packet": str(output),
        "item_count": len(packet["items"]),
        "by_source": counts,
        "classifications_changed": 0,
        "private_content_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
