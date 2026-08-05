from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Prompt6DesktopTests(unittest.TestCase):
    def test_desktop_plugin_uses_only_local_plugin_api_and_no_executor(self):
        source = (ROOT / "hermes/desktop-plugins/hermes-attention/plugin.js").read_text(encoding="utf-8")
        self.assertIn("pluginContext.rest('/tasks'", source)
        self.assertIn("pluginContext.rest('/screen'", source)
        self.assertIn("host.navigate('/starmap')", source)
        self.assertIn("host.stopSpeaking()", source)
        self.assertIn("host.learningGraph()", source)
        self.assertIn("Learning status", source)
        self.assertIn("Sync latest Codex work", source)
        self.assertIn("pluginContext.rest('/codex-sync'", source)
        self.assertIn("Right-click a node", source)
        self.assertIn("Stop speaking", source)
        self.assertIn("ctrl+shift+s", source)
        self.assertNotIn("execute_action", source)
        self.assertNotIn("send_message", source)
        self.assertNotIn("slack", source.lower())
        self.assertNotIn("computer_use", source)

    def test_desktop_backend_has_bounded_routes(self):
        source = (ROOT / ".hermes/plugins/hermes-attention/dashboard/plugin_api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        routes = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "router" and decorator.args:
                    routes.add((decorator.func.attr, ast.literal_eval(decorator.args[0])))
        self.assertEqual({("get", "/home"), ("post", "/tasks"), ("post", "/codex-sync"), ("post", "/screen")}, routes)
        self.assertNotIn("SupervisedActionExecutor", source)
        self.assertNotIn("subprocess", source)
        self.assertIn("run_in_threadpool(_sync_codex_in_worker, body)", source)
        self.assertIn('def _sync_codex_in_worker(body: "CodexSyncRequest")', source)

    def test_desktop_manifest_and_fallback_root_are_valid(self):
        manifest = json.loads(
            (ROOT / ".hermes/plugins/hermes-attention/dashboard/manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual("hermes-attention", manifest["name"])
        launcher = (ROOT / "scripts/launch_daily_hermes.sh").read_text(encoding="utf-8")
        self.assertLess(launcher.index('cd "$ROOT"'), launcher.index("refresh_google_tokens.py"))

    def test_desktop_configuration_merge_keeps_review_gates_and_safe_wake_default(self):
        source = (ROOT / "scripts/configure_hermes_desktop_020.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn('config.setdefault("memory", {})["write_approval"] = True', source)
        self.assertIn('config.setdefault("skills", {})["write_approval"] = True', source)
        self.assertIn('[item for item in disabled if item != "skills"]', source)
        self.assertIn('if "skills" not in cli_tools', source)
        self.assertIn('"prune_builtins": False', source)
        self.assertIn('"consolidate": False', source)
        self.assertIn('wake_word.setdefault("enabled", False)', source)
        self.assertIn('voice["silence_duration"] = 5.5', source)
        self.assertIn('voice["max_recording_seconds"] = 600', source)
        self.assertNotIn('config["wake_word"] = {', source)
        self.assertIn('"surface": "gui"', source)
        self.assertIn('"model": "hey_jarvis"', source)
        self.assertIn('["memory_notifications"] = "on"', source)
        self.assertIn('"model": "deepseek-v4-flash"', source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "_atomic_yaml" for node in ast.walk(tree)))
        self.assertNotIn("api_key", source.lower())
        self.assertNotIn("client_secret", source.lower())

    def test_desktop_voice_patch_speaks_final_answer_with_bounded_progress(self):
        patch = (ROOT / "patches/hermes-v2026.8.3-desktop-voice-response.patch").read_text(encoding="utf-8")
        self.assertIn("I'm checking that now.", patch)
        self.assertIn("message.interim", patch)
        self.assertIn("!m.interim", patch)
        self.assertIn("complete final answer", patch)
        self.assertNotIn("Voice response contract", patch)
        self.assertNotIn("Details for screen:", patch)
        self.assertNotIn("projectVoiceSpeech", patch)
        self.assertNotIn("external-action", patch.lower())

    def test_desktop_voice_reliability_patch_preserves_long_requests(self):
        patch = (ROOT / "patches/hermes-v2026.8.3-desktop-voice-reliability.patch").read_text(encoding="utf-8")
        self.assertIn("VOICE_TURN_SILENCE_MS = 5_500", patch)
        self.assertIn("maxRecordingSeconds", patch)
        self.assertIn("transcribeWithOneRetry", patch)
        self.assertIn("for (let attempt = 0; attempt < 2; attempt += 1)", patch)
        self.assertNotIn("writeFile", patch)
        self.assertNotIn("localStorage", patch)


if __name__ == "__main__":
    unittest.main()
