#!/usr/bin/env python3
"""Import strict-valid owner-only Zoom acceptance evidence into Jarvis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.service import AttentionService  # noqa: E402
from hermes_attention.zoom_acceptance_import import import_zoom_acceptance  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("--private-root", type=Path, default=ROOT / "runtime-data" / "acceptance-private")
    parser.add_argument("--database", type=Path, required=True)
    arguments = parser.parse_args()
    service = AttentionService(database=arguments.database)
    try:
        result = import_zoom_acceptance(service, arguments.response, private_root=arguments.private_root)
    finally:
        service.close()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
