"""Pinned, process-local Hermes bridge for the overlay's narrow cancel control."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import threading
import time
from typing import Callable


_BRIDGE_STARTED = False


class OverlayRuntimeBridge:
    """Translate one owner-only cancel sequence into a no-message interruption."""

    def __init__(self, state_path: Path, cancel_current: Callable[[], bool]) -> None:
        self.state_path = state_path
        self.cancel_current = cancel_current
        self.last_cancel_sequence = self._read_sequence()

    def _read_sequence(self) -> int:
        try:
            info = self.state_path.stat()
            if not stat.S_ISREG(info.st_mode):
                return 0
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                return 0
            payload = json.loads(self.state_path.read_text(encoding="utf-8")[:512])
            value = payload.get("cancel_sequence", 0)
            return value if isinstance(value, int) and value >= 0 else 0
        except (OSError, ValueError, json.JSONDecodeError):
            return 0

    def poll_once(self) -> bool:
        sequence = self._read_sequence()
        if sequence <= self.last_cancel_sequence:
            return False
        self.last_cancel_sequence = sequence
        return bool(self.cancel_current())

    def run(self) -> None:
        while True:
            self.poll_once()
            time.sleep(0.1)


def install_overlay_runtime_bridge(ctx: object) -> bool:
    """Start once inside pinned Hermes 0.19.1 without exposing a runtime tool.

    Hermes' public plugin message-injection facade always queues a follow-up
    model turn after interrupting. Cancel must not do that, so this compatibility
    bridge uses the same process-local ``agent.interrupt()`` seam as Hermes'
    native voice barge-in. Missing or changed internals fail closed.
    """
    global _BRIDGE_STARTED
    raw_path = os.environ.get("HERMES_ATTENTION_OVERLAY_MUTE_STATE", "")
    if _BRIDGE_STARTED or not raw_path:
        return _BRIDGE_STARTED

    def cancel_current() -> bool:
        manager = getattr(ctx, "_manager", None)
        cli = getattr(manager, "_cli_ref", None)
        agent = getattr(cli, "agent", None)
        if cli is None or agent is None or not getattr(cli, "_agent_running", False):
            return False
        try:
            from tools.voice_mode import stop_playback
            stop_playback()
        except (ImportError, RuntimeError):
            pass
        agent.interrupt()
        return True

    bridge = OverlayRuntimeBridge(Path(raw_path), cancel_current)
    threading.Thread(target=bridge.run, daemon=True, name="hermes-attention-overlay-control").start()
    _BRIDGE_STARTED = True
    return True
