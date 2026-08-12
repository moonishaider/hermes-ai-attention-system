#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

required=(
  README.md CHANGELOG_V2.md AGENTS.md FULL_CONTEXT_HANDOFF.md MANIFEST.md
  PACKAGE_VALIDATION_REPORT.md
  CODEX_BOOTSTRAP_PROMPT.md
  CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md
  CODEX_PROMPT_02_IMPLEMENTATION.md
  .hermes-ai-attention-project .codex/config.toml .codex/config.toml.example
  .codex/hooks.json .codex/hooks/pre_tool_use_policy.py
  .codex/hooks/subagent_context.py .codex/hooks/test_pre_tool_use_policy.py
  .codex/rules/safety.rules config/github_scope.example.json
  scripts/preflight_safety.sh scripts/verify_safety_controls.sh
  scripts/test_safety_hook.py scripts/verify_github_access.sh
  scripts/safe_create_private_repo.sh scripts/safe_git_push.sh
)
for f in "${required[@]}"; do
  [[ -f "$f" ]] || { echo "Missing required file: $f" >&2; exit 1; }
done

[[ "$(find docs -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')" -ge 29 ]] || {
  echo "Expected at least 29 numbered documentation files." >&2; exit 1;
}

while IFS= read -r tracked_text; do
  if LC_ALL=C grep -Il $'\r' -- "$tracked_text" >/dev/null 2>&1; then
    echo "CRLF line endings detected in tracked text: $tracked_text" >&2
    exit 1
  fi
done < <(git ls-files '*.md' '*.toml' '*.rules')

for f in scripts/*.sh; do bash -n "$f"; done
python3 - <<'PY_VALIDATE'
import json
import tomllib
from pathlib import Path

for path in (Path('.codex/hooks.json'), Path('config/github_scope.example.json')):
    json.loads(path.read_text())
for path in (Path('.codex/config.toml'), Path('.codex/config.toml.example')):
    tomllib.loads(path.read_text())
PY_VALIDATE
PYTHONDONTWRITEBYTECODE=1 python3 .codex/hooks/test_pre_tool_use_policy.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_safety_hook.py

echo "Package structure, JSON/TOML parsing, shell syntax, and safety-hook tests: OK"
