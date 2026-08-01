#!/usr/bin/env bash
set -u

command -v gh >/dev/null 2>&1 || { echo "GitHub CLI (gh) is not installed or not on PATH."; exit 2; }

echo '=== Authentication ==='
gh auth status || true

echo '=== Authenticated identity ==='
gh api user --jq '{login: .login, name: .name}' 2>/dev/null || echo 'Unable to query authenticated user.'

for owner in moonishaider inside-success; do
  echo "=== Read-only repository visibility: $owner ==="
  if gh repo list "$owner" --limit 200 --json nameWithOwner,isPrivate,visibility,updatedAt --jq '{count: length, repositories: map({nameWithOwner, isPrivate, visibility, updatedAt})}' 2>/dev/null; then
    :
  else
    echo "Unable to list repositories for $owner. Check authentication, organization SSO, and source permissions."
  fi
done
