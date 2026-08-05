#!/usr/bin/env python3
"""Merge Hermes Desktop 0.20 safety and personalization settings.

This script deliberately changes only reviewed, non-secret configuration keys.
It makes timestamped owner-only backups before replacing config or profile
files and never prints their contents.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import stat
import tempfile

import yaml


def _backup(path: Path, backup_dir: Path) -> None:
    if not path.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = backup_dir / path.name
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite backup: {destination}")
    shutil.copy2(path, destination)
    destination.chmod(0o600)


def _atomic_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, sort_keys=False, allow_unicode=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with source.open("rb") as reader, os.fdopen(fd, "wb") as writer:
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(root: Path, hermes_home: Path, *, dry_run: bool) -> Path:
    marker = root / ".hermes-ai-attention-project"
    if not marker.is_file():
        raise RuntimeError(f"marked Hermes project root not found: {root}")

    config_path = hermes_home / "config.yaml"
    if not config_path.is_file():
        raise RuntimeError(f"Hermes config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise RuntimeError("Hermes config must be a mapping")

    config.setdefault("memory", {})["write_approval"] = True
    config.setdefault("skills", {})["write_approval"] = True
    # Permit only Hermes' bounded local skill manager. Community-skill search
    # remains disabled through the separate skills_hub toolset, and every
    # create/edit/archive is held by the approval gate above.
    agent = config.setdefault("agent", {})
    disabled = agent.setdefault("disabled_toolsets", [])
    if not isinstance(disabled, list):
        raise RuntimeError("agent.disabled_toolsets must be a list")
    agent["disabled_toolsets"] = [item for item in disabled if item != "skills"]
    cli_tools = config.setdefault("platform_toolsets", {}).setdefault("cli", [])
    if not isinstance(cli_tools, list):
        raise RuntimeError("platform_toolsets.cli must be a list")
    if "skills" not in cli_tools:
        cli_tools.append("skills")
    config["curator"] = {
        "enabled": True,
        "interval_hours": 168,
        "min_idle_hours": 2,
        "stale_after_days": 30,
        "archive_after_days": 90,
        "consolidate": False,
        "prune_builtins": False,
        "backup": {"enabled": True, "keep": 5},
    }
    wake_word = config.setdefault("wake_word", {})
    if not isinstance(wake_word, dict):
        raise RuntimeError("wake_word must be a mapping")
    # Off is the safe first-install default. Once Syed changes the visible
    # Desktop ear toggle, rerunning this idempotent merge must preserve that
    # explicit choice rather than silently turning listening off again.
    wake_word.setdefault("enabled", False)
    wake_word.update({
        "surface": "gui",
        "input_device": None,
        "provider": "openwakeword",
        "phrase": "hey jarvis",
        "sensitivity": 0.65,
        "confirmation_frames": 3,
        "start_new_session": True,
        "openwakeword": {"model": "hey_jarvis", "inference_framework": "tflite"},
    })
    # Typed Quick Entry should remain quiet. Native voice-conversation mode
    # still speaks replies to microphone-originating turns, so the user gets
    # voice when they ask for it without having long text reports narrated.
    voice = config.setdefault("voice", {})
    voice["auto_tts"] = False
    # The stock 3-second VAD boundary submits during Syed's natural
    # mid-sentence pauses. This remains finite so completed turns do not hang.
    voice["silence_duration"] = 5.5
    config["desktop"] = {
        "repo_scan_enabled": True,
        "repo_scan_roots": [str(root)],
        "repo_scan_exclude_paths": [],
    }
    config.setdefault("display", {})["memory_notifications"] = "on"
    auxiliary = config.setdefault("auxiliary", {})
    auxiliary["background_review"] = {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "timeout": 120,
        "extra_body": {},
    }
    auxiliary["curator"] = {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "timeout": 600,
        "extra_body": {},
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = hermes_home / "backups" / f"prompt6-config-before-merge-{timestamp}"
    if dry_run:
        return backup_dir

    backup_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    _backup(config_path, backup_dir)
    _backup(hermes_home / "SOUL.md", backup_dir)
    _backup(hermes_home / "memories" / "USER.md", backup_dir)

    _atomic_yaml(config_path, config)
    _atomic_copy(root / "hermes" / "SOUL.md", hermes_home / "SOUL.md")
    _atomic_copy(root / "hermes" / "USER.md", hermes_home / "memories" / "USER.md")
    for directory in (hermes_home, hermes_home / "memories", hermes_home / "backups", backup_dir):
        directory.chmod(stat.S_IRWXU)
    return backup_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hermes-home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backup = configure(args.root.resolve(), args.hermes_home.expanduser().resolve(), dry_run=args.dry_run)
    print(f"configuration {'validated' if args.dry_run else 'merged'}; backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
