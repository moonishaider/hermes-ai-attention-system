"""Narrow runtime compatibility guards for the pinned Hermes voice stack."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


def overlay_voice_output_muted() -> bool:
    """Read the ephemeral owner-only launcher mute state, failing unmuted."""
    raw_path = os.environ.get("HERMES_ATTENTION_OVERLAY_MUTE_STATE", "")
    if not raw_path:
        return False
    path = Path(raw_path)
    try:
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            return False
        payload = json.loads(path.read_text(encoding="utf-8")[:256])
        return payload.get("muted") is True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _play_darwin_afplay_only(
    voice_mode: Any,
    file_path: str,
    env_factory: Callable[..., dict[str, str]],
) -> bool:
    """Play once with afplay and treat an interrupted exit as final.

    Hermes 0.19.1 normally falls through to ffplay after ``stop_playback``
    terminates afplay. That restarts the same speech after a successful
    barge-in. macOS already selects afplay as its supported native player, so
    a non-zero exit must end this playback attempt rather than select another
    player.
    """
    if not voice_mode.os.path.isfile(file_path):
        voice_mode.logger.warning("Audio file not found: %s", file_path)
        return False

    proc = None
    try:
        proc = voice_mode.subprocess.Popen(
            ["/usr/bin/afplay", file_path],
            stdout=voice_mode.subprocess.DEVNULL,
            stderr=voice_mode.subprocess.DEVNULL,
            stdin=voice_mode.subprocess.DEVNULL,
            env=env_factory(inherit_credentials=False),
        )
        with voice_mode._playback_lock:
            voice_mode._active_playback = proc
        proc.wait(timeout=300)
        return proc.returncode == 0
    except voice_mode.subprocess.TimeoutExpired:
        voice_mode.logger.warning("System player afplay timed out, killing process")
        if proc is not None:
            proc.kill()
            proc.wait()
        return False
    except Exception as exc:
        voice_mode.logger.debug("System player afplay failed: %s", exc)
        return False
    finally:
        if proc is not None:
            with voice_mode._playback_lock:
                if voice_mode._active_playback is proc:
                    voice_mode._active_playback = None


def install_voice_playback_interrupt_guard() -> bool:
    """Install the macOS-only Hermes 0.19.1 playback fallback guard.

    The patch is process-local, idempotent, and activated only by the trusted
    project launcher/plugin. It neither edits the installed Hermes checkout
    nor changes system audio configuration.
    """
    try:
        import tools.voice_mode as voice_mode
        from tools.environments.local import hermes_subprocess_env
    except ImportError:
        return False

    if voice_mode.platform.system() != "Darwin":
        return False
    if getattr(voice_mode, "_hermes_attention_afplay_guard", False):
        return True

    original = voice_mode._play_audio_file_impl

    def guarded(file_path: str) -> bool:
        if voice_mode.platform.system() != "Darwin":
            return original(file_path)
        if overlay_voice_output_muted():
            return False
        return _play_darwin_afplay_only(
            voice_mode,
            file_path,
            hermes_subprocess_env,
        )

    voice_mode._play_audio_file_impl = guarded
    voice_mode._hermes_attention_afplay_guard = True
    return True
