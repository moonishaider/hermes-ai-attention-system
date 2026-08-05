#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
"$ROOT/scripts/preflight_safety.sh" >/dev/null

install_link() {
  local source="$1"
  local destination="$2"
  mkdir -p "$(dirname "$destination")"
  chmod 700 "$(dirname "$destination")"
  if [[ -L "$destination" ]]; then
    local actual
    actual="$(cd "$(dirname "$destination")" && cd "$(readlink "$destination")" && pwd -P)"
    [[ "$actual" == "$source" ]] || {
      echo "Refusing to replace a different symlink: $destination" >&2
      exit 1
    }
    return
  fi
  [[ ! -e "$destination" ]] || {
    echo "Refusing to overwrite existing path: $destination" >&2
    exit 1
  }
  ln -s "$source" "$destination"
}

install_link \
  "$ROOT/.hermes/plugins/hermes-attention" \
  "$HOME/.hermes/plugins/hermes-attention"
install_link \
  "$ROOT/hermes/desktop-plugins/hermes-attention" \
  "$HOME/.hermes/desktop-plugins/hermes-attention"

echo "Hermes Attention Python and Desktop plugins linked to the marked project."
