#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null
[[ "$#" == 3 && "$1" == origin ]] || { echo 'Usage: safe_git_push.sh origin REVIEWED_BRANCH REVIEWED_HEAD_SHA' >&2; exit 1; }
REMOTE="$1"; REVIEWED_BRANCH="$2"; REVIEWED_SHA="$3"
EXPECTED='https://github.com/moonishaider/hermes-ai-attention-system.git'
FETCH="$(git -C "$ROOT" remote get-url --all origin)"
PUSH="$(git -C "$ROOT" remote get-url --push --all origin)"
[[ "$FETCH" == "$EXPECTED" && "$PUSH" == "$EXPECTED" ]] || { echo 'Refusing non-exact or alternate remote URL.' >&2; exit 1; }
BRANCH="$(git -C "$ROOT" symbolic-ref --quiet --short HEAD)"
HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
[[ "$BRANCH" == "$REVIEWED_BRANCH" && "$HEAD_SHA" == "$REVIEWED_SHA" && "$REVIEWED_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Reviewed branch/commit differs from HEAD.' >&2; exit 1; }
git check-ref-format --branch "$BRANCH" >/dev/null
IDENTITY="$(gh api user --jq .login)"
[[ "$(printf '%s' "$IDENTITY" | tr '[:upper:]' '[:lower:]')" == moonishaider ]] || { echo 'Unexpected GitHub identity.' >&2; exit 1; }
META="$(gh repo view moonishaider/hermes-ai-attention-system --json nameWithOwner,visibility --jq '[.nameWithOwner,.visibility]|join(" ")')"
[[ "$META" == 'moonishaider/hermes-ai-attention-system PUBLIC' ]] || { echo 'Exact repository and PUBLIC visibility not verified.' >&2; exit 1; }
REMOTE_SHA="$(git -C "$ROOT" ls-remote --heads origin "refs/heads/$BRANCH" | awk '{print $1}')"
SCAN_ARGS=(--commit "$HEAD_SHA")
if [[ -n "$REMOTE_SHA" ]]; then
  git -C "$ROOT" cat-file -e "$REMOTE_SHA^{commit}" || { echo 'Fetch the remote branch for a reviewed fast-forward check.' >&2; exit 1; }
  git -C "$ROOT" merge-base --is-ancestor "$REMOTE_SHA" "$HEAD_SHA" || { echo 'Non-fast-forward publication refused.' >&2; exit 1; }
  RANGE="$REMOTE_SHA..$HEAD_SHA"
else
  RANGE="$HEAD_SHA"
fi
while IFS= read -r revision; do [[ -z "$revision" ]] || SCAN_ARGS+=(--commit "$revision"); done < <(git -C "$ROOT" rev-list "$RANGE")
python3 "$ROOT/scripts/secret_scan.py" "${SCAN_ARGS[@]}"
git -C "$ROOT" diff --check
# An explicit SHA/refspec prevents a changing checkout from redirecting publication.
command git -C "$ROOT" push --set-upstream origin "$HEAD_SHA:refs/heads/$BRANCH"
