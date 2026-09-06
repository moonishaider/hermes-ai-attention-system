from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "jarvis_slack_context.py"


def _module():
    spec = importlib.util.spec_from_file_location("jarvis_slack_context", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JarvisSlackContextTests(unittest.TestCase):
    def test_slack_context_is_restricted_to_reviewed_read_only_connections(self):
        module = _module()
        self.assertEqual(module.CONNECTIONS, {
            "inside-success": "slack_inside_success_readonly",
            "mitchell": "slack_mitchell_readonly",
        })
        source = SCRIPT.read_text()
        self.assertIn('tool_name = "slack_search_public_and_private"', source)
        self.assertIn('"write_capability": False', source)
        for forbidden in ("chat_postMessage", "chat.postMessage", "slack_send", "conversations_create"):
            self.assertNotIn(forbidden, source)

    def test_unreviewed_context_fails_closed_as_json(self):
        module = _module()
        original_stdin = sys.stdin
        output = io.StringIO()
        try:
            sys.stdin = io.StringIO('{"context":"personal","days":2}')
            with contextlib.redirect_stdout(output):
                self.assertEqual(module.main(), 1)
        finally:
            sys.stdin = original_stdin
        result = json.loads(output.getvalue())
        self.assertFalse(result["ok"])
        self.assertIn("reviewed client context", result["error"])

    def test_native_dloa_does_not_repeat_eager_slack_injection(self):
        rust = (ROOT / "jarvis" / "src-tauri" / "src" / "lib.rs").read_text()
        self.assertIn('"jarvis_slack_context.py"', rust)
        self.assertIn('"jarvis_dloa.py"', rust)
        self.assertNotIn("slack_context_for_prompt", rust)
        self.assertNotIn("DIRECT READ-ONLY SLACK EVIDENCE", rust)


if __name__ == "__main__":
    unittest.main()
