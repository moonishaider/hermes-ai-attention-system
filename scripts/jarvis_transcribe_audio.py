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
JARVIS_STT_PROMPT = (
    "A personal productivity request to Jarvis. Expected names and terms include: "
    "Syed, Moonis, Hermes, Jarvis, Codex, Inside Success, DLOA, Magic Mike, "
    "Mitchell, Upwork, Slack, Zoom, GitHub, Miami, Karachi. Preserve the "
    "speaker's wording, dates, negation, and technical product names."
)


def _transcribe_openai_guided(path: str) -> dict:
    """Use supported language and prompt hints for the owner's vocabulary."""
    try:
        from openai import OpenAI
        from tools.transcription_tools import _resolve_openai_audio_client_config

        api_key, base_url = _resolve_openai_audio_client_config()
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30, max_retries=0)
        with open(path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model=JARVIS_CLOUD_STT_MODEL,
                file=audio_file,
                response_format="json",
                language="en",
                prompt=JARVIS_STT_PROMPT,
                temperature=0,
            )
        transcript = str(getattr(result, "text", "") or "").strip()
        return {"success": bool(transcript), "transcript": transcript, "provider": "openai"}
    except Exception as exc:
        return {"success": False, "transcript": "", "error": type(exc).__name__}


def transcribe_for_jarvis(path: str, *, cloud_transcriber=None, local_transcriber=None) -> dict:
    """Use the reviewed high-accuracy cloud route, with an explicit local fallback.

    Jarvis recordings are transient and are removed by ``main``.  The cloud
    route uses Hermes' existing scoped OpenAI secret resolver; this script
    never reads, prints, or persists the credential itself.  Setting
    ``JARVIS_STT_PROVIDER=local`` keeps the entire request on this Mac.
    """
    if cloud_transcriber is None or local_transcriber is None:
        from tools.transcription_tools import transcribe_audio

        cloud_transcriber = cloud_transcriber or _transcribe_openai_guided
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
