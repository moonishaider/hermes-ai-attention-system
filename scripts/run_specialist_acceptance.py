#!/usr/bin/env python3
"""Run deterministic specialist and scoped-memory acceptance."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.specialist_acceptance import run_specialist_acceptance  # noqa: E402


def main() -> int:
    result = run_specialist_acceptance(ROOT / "specialists")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
