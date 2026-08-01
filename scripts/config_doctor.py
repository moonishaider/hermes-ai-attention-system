#!/usr/bin/env python3
"""Validate project configuration without reading secrets or external systems."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.cli import main  # noqa: E402

raise SystemExit(main(["doctor"]))
