#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/src" python3 -m unittest discover -s tests -v
