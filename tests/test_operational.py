from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hermes_attention.actions import ActionController
from hermes_attention.config import load_json
from hermes_attention.domain import ActionState, RiskClass
from hermes_attention.executor import ExecutionDenied, SlackDestination, SupervisedActionExecutor
from hermes_attention.history import CodexHistoryBridge
from hermes_attention.policy import PolicyEngine
from hermes_attention.routing import ContextRouter
from hermes_attention.runtime_models import DirectModelClient
from hermes_attention.screen import OneShotScreenCapture
from hermes_attention.overlay import OverlayEvent, OverlayEventBus
from hermes_attention.secrets import configured_keys
from hermes_attention.slack_oauth import (
    SlackOAuthConnection,
    SlackOAuthError,
    build_authorization_url,
    persist_hermes_oauth_state,
    validate_granted_scopes,
)
from hermes_attention.storage import Store


ROOT = Path(__file__).resolve().parents[1]


class OperationalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "state.sqlite3")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_history_batch_is_strictly_bounded(self):
        home = Path(self.temp.name) / "codex"
        home.mkdir()
        lines = "".join('{"id":"%s","timestamp":"2026-04-01T00:00:00Z","text":"bounded history"}\n' % number for number in range(8))
        (home / "history.jsonl").write_text(lines, encoding="utf-8")
        bridge = CodexHistoryBridge(self.store, ContextRouter(load_json(ROOT / "config/contexts.json")), home)
        self.assertEqual(3, bridge.ingest(maximum_records=3)["scanned"])
        self.assertEqual(3, bridge.ingest(maximum_records=3)["scanned"])

    def test_codex_tool_output_is_not_ingested(self):
        home = Path(self.temp.name) / "codex"
        home.mkdir()
        records = (
            '{"type":"response_item","timestamp":"2026-04-01T00:00:00Z","payload":{"type":"function_call_output","output":"private tool output"}}\n'
            '{"type":"response_item","timestamp":"2026-04-01T00:00:01Z","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"safe conversation marker"}]}}\n'
        )
        (home / "history.jsonl").write_text(records, encoding="utf-8")
        bridge = CodexHistoryBridge(self.store, ContextRouter(load_json(ROOT / "config/contexts.json")), home)
        self.assertEqual(1, bridge.ingest(maximum_records=10)["inserted"])
        self.assertEqual([], self.store.search_evidence("private tool output"))
        self.assertEqual(1, len(self.store.search_evidence("safe conversation marker")))

    def test_codex_workspace_provenance_routes_context(self):
        home = Path(self.temp.name) / "codex"
        home.mkdir()
        records = (
            '{"type":"session_meta","timestamp":"2026-04-01T00:00:00Z","payload":{"cwd":"/work/Inside success tv/project"}}\n'
            '{"type":"response_item","timestamp":"2026-04-01T00:00:01Z","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"workspace marker"}]}}\n'
        )
        (home / "history.jsonl").write_text(records, encoding="utf-8")
        bridge = CodexHistoryBridge(self.store, ContextRouter(load_json(ROOT / "config/contexts.json")), home)
        bridge.ingest(maximum_records=10)
        result = self.store.search_evidence("workspace marker")[0]
        self.assertEqual("inside-success", result["contexts"][0]["context_id"])
        self.assertIn("Inside success", result["provenance"]["workspace"])

    def test_one_shot_capture_requires_and_consumes_grant(self):
        capture = OneShotScreenCapture()
        with self.assertRaises(PermissionError):
            capture.capture_interactive_png("wrong")
        grant = capture.grant_once("synthetic explicit test")
        self.assertTrue(grant.token)
        self.assertNotEqual(grant.token, capture.grant_once("new grant").token)

    def test_overlay_event_contains_visible_operational_state(self):
        received = []
        bus = OverlayEventBus()
        bus.subscribe(received.append)
        event = OverlayEvent("working", transcript="heard", status="searching", response="streamed", context="inside-success", source="codex")
        bus.publish(event)
        self.assertEqual(event, received[0])
        encoded = event.to_json()
        for field in ("heard", "searching", "streamed", "inside-success", "codex"):
            self.assertIn(field, encoded)

    def test_supervised_executor_fails_closed_then_fixed_destination_executes(self):
        policy = PolicyEngine(external_writes_enabled=True)
        controller = ActionController(self.store, policy)
        destination = SlackDestination("T_FIXED", "C_FIXED")
        proposal = controller.propose(
            action_type="publish_inside_success_daily_update", context_id="inside-success", risk_class=RiskClass.A2,
            target={"workspace_id": "T_FIXED", "channel_id": "C_FIXED"}, payload={"text": "Synthetic reviewed update"},
        )
        executor = SupervisedActionExecutor(self.store, policy, destination, sender=lambda channel, text: {"ok": True})
        with self.assertRaises(ExecutionDenied):
            executor.execute_daily_report(proposal, approved_hash=proposal.preview_hash)
        controller.verify_approval(proposal, approved_preview_hash=proposal.preview_hash, approval_identity="Syed Moonis Haider")
        previous = os.environ.get("HERMES_ACTIONS_KILL_SWITCH")
        os.environ["HERMES_ACTIONS_KILL_SWITCH"] = "0"
        try:
            self.assertTrue(executor.execute_daily_report(proposal, approved_hash=proposal.preview_hash)["executed"])
            with self.assertRaises(ExecutionDenied):
                executor.execute_daily_report(replace(proposal, target={"workspace_id": "T_FIXED", "channel_id": "C_OTHER"}), approved_hash=proposal.preview_hash)
        finally:
            if previous is None:
                os.environ.pop("HERMES_ACTIONS_KILL_SWITCH", None)
            else:
                os.environ["HERMES_ACTIONS_KILL_SWITCH"] = previous

    def test_secret_status_never_returns_values(self):
        path = Path(self.temp.name) / ".env"
        path.write_text("DEEPSEEK_API_KEY=super-secret\n", encoding="utf-8")
        status = configured_keys(path)
        self.assertTrue(status["DEEPSEEK_API_KEY"])
        self.assertFalse(status["OPENAI_API_KEY"])
        self.assertFalse(status["MCP_GITHUB_PERSONAL_READONLY_API_KEY"])
        self.assertNotIn("super-secret", repr(status))

    def test_direct_model_routes_use_configured_endpoint_and_never_sol(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def read(self): return b'{"choices":[{"message":{"content":"ok"}}],"usage":{"prompt_tokens":3,"completion_tokens":1}}'
        client = DirectModelClient(ROOT / "config/models.json", self.store)
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "synthetic-test-key"}), patch("hermes_attention.runtime_models.urlopen", return_value=Response()) as opened:
            result = client.generate("difficult", "synthetic reasoning")
        self.assertTrue(result["success"])
        self.assertEqual("deepseek-v4-pro", result["model"])
        self.assertNotIn("sol", repr(result).casefold())
        self.assertEqual("https://api.deepseek.com/chat/completions", opened.call_args.args[0].full_url)
        self.assertIn("context", opened.call_args.kwargs)

    def test_smoke_record_does_not_return_provider_text(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def read(self): return b'{"output_text":"HERMES_ROUTE_OK","usage":{"input_tokens":2,"output_tokens":1}}'
        client = DirectModelClient(ROOT / "config/models.json", self.store)
        image = "data:image/png;base64,c3ludGhldGlj"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-test-key"}), patch("hermes_attention.runtime_models.urlopen", return_value=Response()):
            result = client.smoke("vision", image_data_url=image)
        self.assertTrue(result["success"])
        self.assertNotIn("text", result)

    def test_slack_oauth_url_and_grant_are_strictly_read_only(self):
        connection = SlackOAuthConnection(
            name="synthetic", app_id="A_TEST", client_id="C_TEST", client_secret_env="TEST_SECRET",
            server_name="slack_test", server_url="https://mcp.slack.com/mcp",
            resource="https://mcp.slack.com",
            authorization_endpoint="https://slack.com/oauth/v2_user/authorize",
            token_endpoint="https://slack.com/api/oauth.v2.user.access",
            redirect_uri="http://127.0.0.1:8765/callback",
            scopes=("search:read.public", "channels:history"),
        )
        url = build_authorization_url(connection, "state", "x" * 72)
        self.assertIn("search%3Aread.public", url)
        self.assertNotIn("chat%3Awrite", url)
        self.assertEqual(connection.scopes, validate_granted_scopes(connection.scopes, "search:read.public channels:history"))
        self.assertEqual(connection.scopes, validate_granted_scopes(connection.scopes, "search:read.public,channels:history"))
        with self.assertRaises(SlackOAuthError):
            validate_granted_scopes(connection.scopes, "search:read.public chat:write")

    def test_slack_oauth_persistence_is_mode_600_and_result_has_no_tokens(self):
        connection = SlackOAuthConnection(
            name="synthetic", app_id="A_TEST", client_id="C_TEST", client_secret_env="TEST_SECRET",
            server_name="slack_test", server_url="https://mcp.slack.com/mcp",
            resource="https://mcp.slack.com",
            authorization_endpoint="https://slack.com/oauth/v2_user/authorize",
            token_endpoint="https://slack.com/api/oauth.v2.user.access",
            redirect_uri="http://127.0.0.1:8765/callback",
            scopes=("search:read.public",),
        )
        token_dir = Path(self.temp.name) / "tokens"
        result = persist_hermes_oauth_state(connection, "client-secret", {
            "ok": True, "access_token": "access-secret", "refresh_token": "refresh-secret",
            "scope": "search:read.public", "expires_in": 3600,
        }, token_dir=token_dir)
        self.assertTrue(result["stored"])
        self.assertNotIn("access-secret", repr(result))
        self.assertNotIn("client-secret", repr(result))
        for path in token_dir.iterdir():
            self.assertEqual(0o600, path.stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
