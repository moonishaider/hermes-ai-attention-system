#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
MARKER="$PROJECT_ROOT/.hermes-ai-attention-project"

if [[ ! -f "$MARKER" ]]; then
  echo "Refusing to install: marked project root not found." >&2
  exit 1
fi

RUNTIME_ROOT="$HOME/.hermes/jarvis-runtime"
PLUGIN_LINK="$HOME/.hermes/plugins/hermes-attention"
DESKTOP_PLUGIN_LINK="$HOME/.hermes/desktop-plugins/hermes-attention"
BACKUP_ROOT="$HOME/.hermes/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$RUNTIME_ROOT" "$BACKUP_ROOT" "$(dirname -- "$PLUGIN_LINK")" "$(dirname -- "$DESKTOP_PLUGIN_LINK")"
chmod 700 "$RUNTIME_ROOT"

if [[ -d "$RUNTIME_ROOT/src" || -d "$RUNTIME_ROOT/config" ]]; then
  BACKUP="$BACKUP_ROOT/jarvis-runtime-before-$STAMP"
  mkdir -p "$BACKUP"
  chmod 700 "$BACKUP"
  for name in .hermes-ai-attention-project src config specialists scripts .hermes hermes; do
    if [[ -e "$RUNTIME_ROOT/$name" ]]; then
      rsync -a "$RUNTIME_ROOT/$name" "$BACKUP/"
    fi
  done
fi

for name in .hermes-ai-attention-project src config specialists scripts .hermes hermes; do
  if [[ ! -e "$PROJECT_ROOT/$name" ]]; then
    echo "Refusing to install: missing required runtime path $name." >&2
    exit 1
  fi
  rsync -a "$PROJECT_ROOT/$name" "$RUNTIME_ROOT/"
done

# The operational database is copied only for the first runtime install. Later
# installs update code/config without replacing current evidence or state.
mkdir -p "$RUNTIME_ROOT/runtime-data"
chmod 700 "$RUNTIME_ROOT/runtime-data"
if [[ ! -f "$RUNTIME_ROOT/runtime-data/hermes_attention.sqlite3" ]]; then
  SOURCE_DB="$PROJECT_ROOT/runtime-data/hermes_attention.sqlite3"
  if [[ -f "$SOURCE_DB" ]]; then
    cp -p "$SOURCE_DB" "$RUNTIME_ROOT/runtime-data/hermes_attention.sqlite3"
    chmod 600 "$RUNTIME_ROOT/runtime-data/hermes_attention.sqlite3"
  fi
fi

if [[ -L "$PLUGIN_LINK" ]]; then
  CURRENT_TARGET="$(readlink "$PLUGIN_LINK")"
  case "$CURRENT_TARGET" in
    "$PROJECT_ROOT/.hermes/plugins/hermes-attention"|"$RUNTIME_ROOT/.hermes/plugins/hermes-attention") ;;
    *)
      echo "Refusing to replace an unrelated Hermes plugin link: $PLUGIN_LINK" >&2
      exit 1
      ;;
  esac
elif [[ -e "$PLUGIN_LINK" ]]; then
  echo "Refusing to replace a non-link Hermes plugin: $PLUGIN_LINK" >&2
  exit 1
fi
ln -sfn "$RUNTIME_ROOT/.hermes/plugins/hermes-attention" "$PLUGIN_LINK"

if [[ -L "$DESKTOP_PLUGIN_LINK" ]]; then
  CURRENT_DESKTOP_TARGET="$(readlink "$DESKTOP_PLUGIN_LINK")"
  case "$CURRENT_DESKTOP_TARGET" in
    "$PROJECT_ROOT/hermes/desktop-plugins/hermes-attention"|"$RUNTIME_ROOT/hermes/desktop-plugins/hermes-attention") ;;
    *)
      echo "Refusing to replace an unrelated Hermes desktop plugin link: $DESKTOP_PLUGIN_LINK" >&2
      exit 1
      ;;
  esac
elif [[ -e "$DESKTOP_PLUGIN_LINK" ]]; then
  echo "Refusing to replace a non-link Hermes desktop plugin: $DESKTOP_PLUGIN_LINK" >&2
  exit 1
fi
ln -sfn "$RUNTIME_ROOT/hermes/desktop-plugins/hermes-attention" "$DESKTOP_PLUGIN_LINK"

echo "Jarvis runtime installed at $RUNTIME_ROOT"
echo "Operational database preserved at $RUNTIME_ROOT/runtime-data/hermes_attention.sqlite3"
