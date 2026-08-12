from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from scripts.jarvis_transcribe_audio import JARVIS_CLOUD_STT_MODEL, JARVIS_STT_PROMPT, transcribe_for_jarvis


class JarvisTranscriptionTests(unittest.TestCase):
    def test_cloud_transcription_is_primary(self) -> None:
        cloud = Mock(return_value={"success": True, "transcript": "accurate", "provider": "openai"})
        local = Mock()
        result = transcribe_for_jarvis(
            "recording.webm", cloud_transcriber=cloud, local_transcriber=local
        )
        self.assertEqual(result["transcript"], "accurate")
        local.assert_not_called()

    def test_default_cloud_route_uses_high_accuracy_model(self) -> None:
        self.assertEqual(JARVIS_CLOUD_STT_MODEL, "gpt-4o-transcribe")
        self.assertIn("Inside Success", JARVIS_STT_PROMPT)
        self.assertIn("DLOA", JARVIS_STT_PROMPT)
        self.assertIn("negation", JARVIS_STT_PROMPT)

    def test_local_transcription_is_a_visible_fallback(self) -> None:
        cloud = Mock(return_value={"success": False, "error": "offline"})
        local = Mock(return_value={"success": True, "transcript": "local", "provider": "local"})
        result = transcribe_for_jarvis(
            "recording.webm", cloud_transcriber=cloud, local_transcriber=local
        )
        self.assertEqual(result["transcript"], "local")
        self.assertEqual(result["fallback_from"], "openai")

    def test_owner_can_force_local_only(self) -> None:
        cloud = Mock()
        local = Mock(return_value={"success": True, "transcript": "private", "provider": "local"})
        with patch.dict(os.environ, {"JARVIS_STT_PROVIDER": "local"}):
            result = transcribe_for_jarvis(
                "recording.webm", cloud_transcriber=cloud, local_transcriber=local
            )
            self.assertEqual(result["provider"], "local")
            cloud.assert_not_called()
