#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/test_safety_hook.py"

if command -v codex >/dev/null 2>&1; then
  RULES="$ROOT/.codex/rules/safety.rules"
  check_forbidden() {
    local output
    output="$(codex execpolicy check --pretty --rules "$RULES" -- "$@")"
    printf '%s\n' "$output"
    printf '%s' "$output" | grep -q 'forbidden' || {
      echo "Expected forbidden decision for: $*" >&2
      exit 1
    }
  }
  check_forbidden rm -rf /tmp/example
  check_forbidden git push origin main
  check_forbidden gh repo create moonishaider/hermes-ai-attention-system --private
else
  echo "Codex CLI not found; skipped execpolicy CLI checks. Hook tests still passed."
fi

echo "All available safety-control checks passed."
