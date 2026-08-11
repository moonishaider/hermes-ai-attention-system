#!/usr/bin/env python3
"""Transcribe one bounded stdin recording through Hermes voice configuration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


HERMES_ROOT = Path.home() / ".hermes" / "hermes-agent"
sys.path.insert(0, str(HERMES_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", choices=(".webm", ".wav", ".mp4", ".m4a"), required=True)
    args = parser.parse_args()
    recording = sys.stdin.buffer.read(15_000_001)
    if not recording or len(recording) > 15_000_000:
        print(json.dumps({"ok": False, "error": "recording must contain 1 to 15 MB"}))
        return 2
    path = ""
    try:
        with tempfile.NamedTemporaryFile(prefix="jarvis-voice-", suffix=args.suffix, delete=False) as handle:
            handle.write(recording)
            path = handle.name
        os.chmod(path, 0o600)
        from tools.voice_mode import transcribe_recording

        result = transcribe_recording(path)
        transcript = str(result.get("transcript") or "").strip()
        print(json.dumps({
            "ok": bool(result.get("success")) or not transcript,
            "transcript": transcript,
            "provider": result.get("provider"),
            "error": None if result.get("success") else str(result.get("error") or "transcription failed"),
        }))
        return 0 if result.get("success") or not transcript else 1
    finally:
        recording = b""
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
