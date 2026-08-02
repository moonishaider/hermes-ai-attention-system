#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null
export HERMES_ENABLE_PROJECT_PLUGINS=1
export HERMES_ACTIONS_KILL_SWITCH="${HERMES_ACTIONS_KILL_SWITCH:-1}"
export PYTHONPATH="$ROOT/src"

python3 -m hermes_attention.cli health

OVERLAY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hermes-attention-overlay.XXXXXX")"
FIFO="$OVERLAY_DIR/events"
mkfifo "$FIFO"
chmod 600 "$FIFO"
OVERLAY_PID=""
FEED_PID=""
cleanup() {
  if [[ -n "$FEED_PID" ]]; then kill "$FEED_PID" 2>/dev/null || true; fi
  if [[ -n "$OVERLAY_PID" ]]; then kill "$OVERLAY_PID" 2>/dev/null || true; fi
  rm -f "$FIFO"
  rmdir "$OVERLAY_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 -m hermes_attention.cli overlay <"$FIFO" &
OVERLAY_PID=$!
{
  printf '%s\n' '{"state":"ready","transcript":"Microphone is off until explicitly started","status":"Hermes ready; external actions killed","response":"","context":"unknown","source":"startup"}'
  while true; do sleep 30; done
} >"$FIFO" &
FEED_PID=$!

cd "$ROOT"
"$HOME/.local/bin/hermes" "$@"
