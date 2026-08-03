#!/usr/bin/env python3
"""Apply only explicit owner decisions from one private calibration packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.calibration import apply_context_calibration  # noqa: E402
from hermes_attention.config import load_json  # noqa: E402
from hermes_attention.storage import Store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--confirmed-by", default="")
    arguments = parser.parse_args()
    packet_path = arguments.packet.resolve()
    private_root = (ROOT / "runtime-data/calibration-private").resolve()
    try:
        packet_path.relative_to(private_root)
    except ValueError:
        parser.error("packet must be below runtime-data/calibration-private")
    if not arguments.confirmed:
        parser.error("explicit --confirmed is required after owner review")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    contexts = load_json(ROOT / "config/contexts.json")
    allowed = {item["id"] for item in contexts.get("contexts", [])}
    with Store(ROOT / "runtime-data/hermes_attention.sqlite3") as store:
        result = apply_context_calibration(store, packet, confirmed_by=arguments.confirmed_by, allowed_contexts=allowed)
    print(json.dumps({**result, "private_content_printed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
