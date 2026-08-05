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
        self.assertEqual({("get", "/home"), ("post", "/tasks"), ("post", "/screen")}, routes)
        self.assertNotIn("SupervisedActionExecutor", source)
        self.assertNotIn("subprocess", source)

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
        self.assertNotIn('config["wake_word"] = {', source)
        self.assertIn('"surface": "gui"', source)
        self.assertIn('"model": "hey_jarvis"', source)
        self.assertIn('["memory_notifications"] = "on"', source)
        self.assertIn('"model": "deepseek-v4-flash"', source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "_atomic_yaml" for node in ast.walk(tree)))
        self.assertNotIn("api_key", source.lower())
        self.assertNotIn("client_secret", source.lower())

    def test_desktop_voice_patch_separates_spoken_and_screen_detail(self):
        patch = (ROOT / "patches/hermes-v2026.8.3-desktop-voice-response.patch").read_text(encoding="utf-8")
        self.assertIn("Voice response contract", patch)
        self.assertIn("Details for screen:", patch)
        self.assertIn("displayText: text", patch)
        self.assertIn("projectVoiceSpeech", patch)
        self.assertNotIn("external-action", patch.lower())


if __name__ == "__main__":
    unittest.main()
