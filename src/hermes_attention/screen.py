"""Explicit, one-time macOS capture adapter with no automatic retention."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
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
        # macOS 26 no longer streams interactive captures to ``-`` or
        # ``/dev/stdout``. Use one owner-only random temporary directory,
        # read the selected PNG once, and guarantee removal before returning.
        with tempfile.TemporaryDirectory(prefix="hermes-screen-") as temp_dir:
            os.chmod(temp_dir, 0o700)
            capture_path = Path(temp_dir) / "one-shot.png"
            try:
                result = subprocess.run(
                    [
                        "/usr/sbin/screencapture", "-i", "-s", "-o", "-x",
                        "-t", "png", str(capture_path),
                    ],
                    check=False, capture_output=True, timeout=120,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("interactive capture timed out without a selection") from exc
            if result.returncode != 0 or not capture_path.is_file():
                raise RuntimeError("capture cancelled, permission denied, or no PNG returned")
            os.chmod(capture_path, 0o600)
            png = capture_path.read_bytes()
            if not png.startswith(b"\x89PNG"):
                raise RuntimeError("interactive capture did not return a PNG")
            return png
