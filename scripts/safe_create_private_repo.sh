#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null

OWNER="moonishaider"
REPO="${1:-hermes-ai-attention-system}"

[[ "$REPO" =~ ^hermes-ai-attention-system([._-][A-Za-z0-9._-]+)?$ ]] || {
  echo "Refusing repository name outside the approved project namespace: $REPO" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || { echo "GitHub CLI is required." >&2; exit 2; }

LOGIN="$(gh api user --jq .login 2>/dev/null || true)"
[[ "${LOGIN,,}" == "${OWNER,,}" ]] || {
  echo "Refusing creation: active GitHub identity is '${LOGIN:-unknown}', expected '$OWNER'." >&2
  echo "Switch the GitHub CLI to the personal account before retrying." >&2
  exit 3
}

git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "Initialize Git and create a baseline commit before creating the remote." >&2
  exit 1
}

if git -C "$ROOT" remote get-url origin >/dev/null 2>&1; then
  echo "Refusing creation because an origin remote already exists. Inspect it manually." >&2
  exit 4
fi

if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  echo "Repository $OWNER/$REPO already exists; refusing to overwrite or repurpose it automatically." >&2
  echo "Inspect it manually or choose a safe project-name suffix." >&2
  exit 5
fi

( cd "$ROOT" && gh repo create "$OWNER/$REPO" --private --source . --remote origin )

VISIBILITY="$(gh repo view "$OWNER/$REPO" --json visibility --jq .visibility 2>/dev/null || true)"
[[ "$VISIBILITY" == "PRIVATE" ]] || {
  echo "Repository was created but private visibility could not be verified. Do not push." >&2
  exit 6
}

echo "Created and verified private repository: $OWNER/$REPO"
echo "No push was performed. Use scripts/safe_git_push.sh after diff and secret review."
