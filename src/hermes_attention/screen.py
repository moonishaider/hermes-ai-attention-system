"""Explicit, one-time macOS capture adapter with no automatic retention."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ScreenGrant:
    token: str
    reason: str


class OneShotScreenCapture:
    def __init__(self) -> None:
        self._grant: ScreenGrant | None = None

    def grant_once(self, reason: str) -> ScreenGrant:
        if not reason.strip():
            raise ValueError("an explicit capture reason is required")
        self._grant = ScreenGrant(str(uuid4()), reason.strip())
        return self._grant

    def capture_interactive_png(self, token: str) -> bytes:
        if not self._grant or self._grant.token != token:
            raise PermissionError("missing or invalid one-time screen grant")
        self._grant = None
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-i", "-o", "-t", "png", "-"],
            check=False, capture_output=True, timeout=120,
        )
        if result.returncode != 0 or not result.stdout.startswith(b"\x89PNG"):
            raise RuntimeError("capture cancelled, permission denied, or no PNG returned")
        return result.stdout
