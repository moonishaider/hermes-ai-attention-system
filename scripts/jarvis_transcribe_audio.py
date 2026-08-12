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
JARVIS_CLOUD_STT_MODEL = "gpt-4o-transcribe"


def transcribe_for_jarvis(path: str, *, cloud_transcriber=None, local_transcriber=None) -> dict:
    """Use the reviewed high-accuracy cloud route, with an explicit local fallback.

    Jarvis recordings are transient and are removed by ``main``.  The cloud
    route uses Hermes' existing scoped OpenAI secret resolver; this script
    never reads, prints, or persists the credential itself.  Setting
    ``JARVIS_STT_PROVIDER=local`` keeps the entire request on this Mac.
    """
    if cloud_transcriber is None or local_transcriber is None:
        from tools.transcription_tools import _transcribe_openai, transcribe_audio

        cloud_transcriber = cloud_transcriber or (
            lambda recording: _transcribe_openai(recording, JARVIS_CLOUD_STT_MODEL)
        )
        local_transcriber = local_transcriber or transcribe_audio

    if os.getenv("JARVIS_STT_PROVIDER", "cloud").strip().lower() == "local":
        return local_transcriber(path)

    cloud = cloud_transcriber(path)
    if cloud.get("success"):
        return cloud

    local = local_transcriber(path)
    if local.get("success"):
        local["fallback_from"] = "openai"
        return local
    return {
        "success": False,
        "transcript": "",
        "provider": "unavailable",
        "error": "cloud and local transcription both failed",
    }


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
        result = transcribe_for_jarvis(path)
        transcript = str(result.get("transcript") or "").strip()
        print(json.dumps({
            "ok": bool(result.get("success")),
            "transcript": transcript,
            "provider": result.get("provider"),
            "fallback_from": result.get("fallback_from"),
            "error": None if result.get("success") else str(result.get("error") or "transcription failed"),
        }))
        return 0 if result.get("success") else 1
    finally:
        recording = b""
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
