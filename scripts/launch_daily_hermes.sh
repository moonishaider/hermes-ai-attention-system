#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null
export HERMES_ENABLE_PROJECT_PLUGINS=1
export HERMES_ACTIONS_KILL_SWITCH="${HERMES_ACTIONS_KILL_SWITCH:-1}"
export PYTHONPATH="$ROOT/src"

python3 "$ROOT/scripts/refresh_google_tokens.py"
python3 -m hermes_attention.cli health

OVERLAY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hermes-attention-overlay.XXXXXX")"
FIFO="$OVERLAY_DIR/events"
CONTROL_FIFO="$OVERLAY_DIR/controls"
MUTE_STATE="$OVERLAY_DIR/mute-state.json"
CONTROL_AUDIT_DIR="$ROOT/runtime-data/overlay-private"
CONTROL_AUDIT="$CONTROL_AUDIT_DIR/control-audit.jsonl"
HERMES_AGENT_PATH="$HOME/.hermes/hermes-agent/hermes"
mkfifo "$FIFO"
mkfifo "$CONTROL_FIFO"
chmod 600 "$FIFO" "$CONTROL_FIFO"
mkdir -p "$CONTROL_AUDIT_DIR"
chmod 700 "$CONTROL_AUDIT_DIR"
export HERMES_ATTENTION_OVERLAY_CONTROL_FIFO="$CONTROL_FIFO"
export HERMES_ATTENTION_OVERLAY_MUTE_STATE="$MUTE_STATE"
OVERLAY_PID=""
FEED_PID=""
CONTROL_PID=""
cleanup() {
  if [[ -n "$FEED_PID" ]]; then kill "$FEED_PID" 2>/dev/null || true; fi
  if [[ -n "$OVERLAY_PID" ]]; then kill "$OVERLAY_PID" 2>/dev/null || true; fi
  if [[ -n "$CONTROL_PID" ]]; then kill "$CONTROL_PID" 2>/dev/null || true; fi
  rm -f "$FIFO" "$CONTROL_FIFO" "$MUTE_STATE"
  rmdir "$OVERLAY_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 -m hermes_attention.cli overlay-control \
  --fifo "$CONTROL_FIFO" \
  --launcher-pid "$$" \
  --hermes-path "$HERMES_AGENT_PATH" \
  --mute-state "$MUTE_STATE" \
  --audit "$CONTROL_AUDIT" &
CONTROL_PID=$!
python3 -m hermes_attention.cli overlay <"$FIFO" &
OVERLAY_PID=$!
{
  printf '%s\n' '{"state":"ready","transcript":"Microphone is off until explicitly started","status":"Hermes ready; external actions killed","response":"","context":"unknown","source":"startup"}'
  while true; do sleep 30; done
} >"$FIFO" &
FEED_PID=$!

cd "$ROOT"
"$HOME/.local/bin/hermes" "$@"
