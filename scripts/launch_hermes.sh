#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null
export HERMES_ENABLE_PROJECT_PLUGINS=1
export HERMES_ACTIONS_KILL_SWITCH="${HERMES_ACTIONS_KILL_SWITCH:-1}"
cd "$ROOT"
exec "$HOME/.local/bin/hermes" "$@"
