#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null

REMOTE="${1:-origin}"
[[ "$#" -le 1 ]] || { echo "Only an optional remote name is accepted; arbitrary push flags are forbidden." >&2; exit 1; }

URL="$(git -C "$ROOT" remote get-url "$REMOTE")"
case "$URL" in
  git@github.com:moonishaider/hermes-ai-attention-system*.git|https://github.com/moonishaider/hermes-ai-attention-system*.git|https://github.com/moonishaider/hermes-ai-attention-system*)
    ;;
  *)
    echo "Refusing push to unapproved remote: $URL" >&2
    exit 1
    ;;
esac

printf '%s' "$URL" | grep -q 'inside-success' && {
  echo "Refusing any implementation push to inside-success." >&2
  exit 1
}

BRANCH="$(git -C "$ROOT" symbolic-ref --quiet --short HEAD || true)"
[[ -n "$BRANCH" ]] || { echo "Refusing push from a detached HEAD." >&2; exit 1; }

REPO="$(printf '%s' "$URL" | sed -E 's#^git@github.com:##; s#^https://github.com/##; s#\.git$##')"
VISIBILITY="$(gh repo view "$REPO" --json visibility --jq .visibility 2>/dev/null || true)"
[[ "$VISIBILITY" == "PRIVATE" ]] || {
  echo "Refusing push because private visibility was not verified for $REPO." >&2
  exit 1
}

# Reject tracked files with secret-bearing names. Templates/examples are allowed.
BAD_NAMES="$(git -C "$ROOT" ls-files | grep -Ei '(^|/)(\.env$|auth\.json$|credentials?\.(json|ya?ml|toml)$|.*token.*\.(json|txt|ya?ml|toml)$|.*secret.*\.(json|txt|ya?ml|toml)$|id_(rsa|ed25519)$)' | grep -Evi '(example|sample|template)' || true)"
if [[ -n "$BAD_NAMES" ]]; then
  echo "Refusing push because tracked files look secret-bearing:" >&2
  echo "$BAD_NAMES" >&2
  exit 1
fi

# Detect several high-confidence credential formats in tracked content. This is
# supplemental; the implementation must also use a real secret scanner.
BAD_CONTENT="$(git -C "$ROOT" grep -IlE '(github_pat_[A-Za-z0-9_]{40,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)' -- . ':!*.example' ':!*.sample' ':!*.template' 2>/dev/null || true)"
if [[ -n "$BAD_CONTENT" ]]; then
  echo "Refusing push because tracked content matches a high-confidence secret pattern:" >&2
  echo "$BAD_CONTENT" >&2
  exit 1
fi

if command -v gitleaks >/dev/null 2>&1; then
  ( cd "$ROOT" && gitleaks git --no-banner --redact )
else
  echo "Note: gitleaks is not installed; filename and high-confidence content checks were used."
fi

git -C "$ROOT" diff --check
git -C "$ROOT" status --short

# No force, mirror, delete, prune, tags, or arbitrary refspecs are accepted.
if git -C "$ROOT" ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>&1; then
  ( cd "$ROOT" && command git push "$REMOTE" "$BRANCH" )
else
  ( cd "$ROOT" && command git push --set-upstream "$REMOTE" "$BRANCH" )
fi
