#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MARKER="$ROOT/.hermes-ai-attention-project"

fail() { printf 'PRECHECK FAILED: %s\n' "$1" >&2; exit 1; }

[[ -f "$MARKER" ]] || fail "project marker is missing"
[[ -f "$ROOT/AGENTS.md" ]] || fail "AGENTS.md is missing"
[[ -f "$ROOT/FULL_CONTEXT_HANDOFF.md" ]] || fail "FULL_CONTEXT_HANDOFF.md is missing"
[[ -f "$ROOT/.codex/config.toml" ]] || fail "project Codex configuration is missing"
[[ -f "$ROOT/.codex/hooks.json" ]] || fail "Codex hooks configuration is missing"
[[ -f "$ROOT/.codex/hooks/pre_tool_use_policy.py" ]] || fail "PreToolUse safety hook is missing"
[[ -f "$ROOT/.codex/hooks/subagent_context.py" ]] || fail "Subagent safety hook is missing"
[[ -f "$ROOT/.codex/rules/safety.rules" ]] || fail "Codex safety rules are missing"

HOME_REAL="$(cd "$HOME" && pwd -P)"
case "$ROOT" in
  /|"$HOME_REAL"|"$HOME_REAL/Desktop"|"$HOME_REAL/Documents"|"$HOME_REAL/Downloads")
    fail "unsafe project root: $ROOT"
    ;;
esac

[[ ! -L "$ROOT" ]] || fail "project root must not be a symlink"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import os, sys
root = Path(sys.argv[1]).resolve()
for base, dirs, files in os.walk(root, followlinks=False):
    for name in [*dirs, *files]:
        p = Path(base) / name
        if not p.is_symlink():
            continue
        target = p.resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError:
            print(f"PRECHECK FAILED: symlink leaves project: {p} -> {target}", file=sys.stderr)
            raise SystemExit(1)
PY

printf 'Project root: %s\n' "$ROOT"
printf 'Project marker: OK\n'
printf 'Symlink boundary: OK\n'
printf 'Codex configuration, hooks, and rules: OK\n'

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_ROOT="$(git -C "$ROOT" rev-parse --show-toplevel)"
  [[ "$GIT_ROOT" == "$ROOT" ]] || fail "Git root differs from marked project root: $GIT_ROOT"
  printf 'Git root: %s\n' "$GIT_ROOT"

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    remote="${line%%[[:space:]]*}"
    url="${line#*[[:space:]]}"
    case "$url" in
      git@github.com:moonishaider/hermes-ai-attention-system*.git|https://github.com/moonishaider/hermes-ai-attention-system*.git|https://github.com/moonishaider/hermes-ai-attention-system*) ;;
      *) fail "unapproved Git remote $remote: $url" ;;
    esac
  done < <(git -C "$ROOT" remote -v 2>/dev/null | awk '$3=="(push)" {print $1 " " $2}' | sort -u)

  BAD="$(git -C "$ROOT" ls-files | grep -Ei '(^|/)(\.env$|auth\.json$|credentials?\.(json|ya?ml|toml)$|.*token.*\.(json|txt|ya?ml|toml)$|.*secret.*\.(json|txt|ya?ml|toml)$)' | grep -Evi '(example|sample|template)' || true)"
  [[ -z "$BAD" ]] || fail "tracked files look secret-bearing: $BAD"

  git -C "$ROOT" status --short
else
  printf 'Git repository: not initialized yet (allowed before Prompt 2)\n'
fi

printf 'Safety preflight passed.\n'
