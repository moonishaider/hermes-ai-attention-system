#!/usr/bin/env python3
"""Create a disabled specialist skeleton after validating a safe identifier."""

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("specialist_id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", args.specialist_id):
        parser.error("specialist_id must be lowercase kebab-case")
    root = args.root.resolve()
    specialists = root / "specialists"
    target = (specialists / args.specialist_id).resolve()
    if specialists not in target.parents or target.exists():
        parser.error("target is unsafe or already exists")
    target.mkdir(parents=True)
    (target / "instructions.md").write_text(
        f"# {args.specialist_id}\n\nDisabled skeleton. Define evidence, context, tool, and action boundaries before registration.\n",
        encoding="utf-8",
    )
    print(f"Created disabled skeleton: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
