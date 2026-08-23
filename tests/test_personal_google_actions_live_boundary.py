from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

import unittest
from unittest.mock import patch

from hermes_attention.personal_google_action_oauth import (
    PERSONAL_ACTION_SCOPES, PersonalGoogleActionTokenManager,
)
from hermes_attention.personal_google_actions import PersonalGoogleActionTransport
from hermes_attention.storage import Store
from hermes_attention.computer_awareness import AwarenessPolicy, ComputerAwareness

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _private_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


ALLOWED = [
    ("POST", "https://www.googleapis.com/calendar/v3/calendars/primary/events"),
    ("PATCH", "https://www.googleapis.com/calendar/v3/calendars/primary/events/event_1"),
    ("DELETE", "https://www.googleapis.com/calendar/v3/calendars/primary/events/event_1"),
    ("POST", "https://gmail.googleapis.com/gmail/v1/users/me/drafts"),
    ("PUT", "https://gmail.googleapis.com/gmail/v1/users/me/drafts/draft_1"),
    ("GET", "https://gmail.googleapis.com/gmail/v1/users/me/drafts/draft_1"),
]


BLOCKED = [
    ("POST", "https://gmail.googleapis.com/gmail/v1/users/me/drafts/send"),
    ("POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"),
    ("DELETE", "https://gmail.googleapis.com/gmail/v1/users/me/drafts/draft_1"),
    ("POST", "https://www.googleapis.com/calendar/v3/calendars/work/events"),
    ("GET", "https://www.googleapis.com/calendar/v3/calendars/primary/events"),
    ("POST", "http://www.googleapis.com/calendar/v3/calendars/primary/events"),
]


class PersonalGoogleLiveBoundaryTests(unittest.TestCase):
    def test_focus_pause_resume_and_ninety_minute_window_are_explicit(self) -> None:
        with Store(":memory:") as store:
            awareness = ComputerAwareness(store)
            focus_id = awareness.start_focus(
                context_id="personal", minutes=90, policy=AwarenessPolicy(),
            )
            awareness.pause(focus_id)
            with self.assertRaises(PermissionError):
                awareness.observe_metadata(
                    focus_id=focus_id, app_id="com.openai.codex", window_title="Project",
                    domain=None, browser_profile=None, context_id="personal",
                )
            awareness.resume(focus_id)
            event_id = awareness.observe_metadata(
                focus_id=focus_id, app_id="com.openai.codex", window_title="Project",
                domain=None, browser_profile=None, context_id="personal",
            )
            self.assertTrue(event_id)

    def test_owner_callback_allows_deliberate_consent_review(self) -> None:
        source = (ROOT / "scripts" / "authorize_personal_google_actions.py").read_text()
        self.assertIn("deadline = time.monotonic() + 900", source)
        self.assertIn('while time.monotonic() < deadline and not result.get("code")', source)
        self.assertIn("server.handle_request()", source)

    def test_action_oauth_is_separate_exact_and_does_not_union_read_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _private_json(root / "google_personal_calendar_readonly.client.json", {
                "client_id": "test-client", "client_secret": "test-secret",
                "redirect_uris": ["http://127.0.0.1:8765/callback"],
            })
            manager = PersonalGoogleActionTokenManager(root)
            request = manager.authorization_request()
            query = parse_qs(urlparse(request["url"]).query)
            self.assertEqual(set(query["scope"][0].split()), set(PERSONAL_ACTION_SCOPES))
            self.assertEqual(query["include_granted_scopes"], ["false"])
            self.assertEqual(query["login_hint"], ["moonishaider12@gmail.com"])
            self.assertFalse((root / "google_personal_actions.json").exists())

    def test_transport_allows_only_reviewed_personal_methods(self) -> None:
        for method, url in ALLOWED:
            with self.subTest(method=method, url=url):
                self.assertTrue(PersonalGoogleActionTransport._allowed(method, url))

    def test_transport_has_no_send_work_calendar_or_generic_surface(self) -> None:
        for method, url in BLOCKED:
            with self.subTest(method=method, url=url):
                self.assertFalse(PersonalGoogleActionTransport._allowed(method, url))

    def test_personal_capabilities_default_off_independently_of_token_presence(self) -> None:
        import jarvis_local_state as local_state

        with tempfile.TemporaryDirectory() as directory:
            with Store(Path(directory) / "state.sqlite3") as store:
                class Service:
                    pass
                service = Service()
                service.store = store
                self.assertFalse(local_state._personal_actions_enabled(service))
                self.assertEqual(local_state._personal_action_mode(service), "off")
                local_state._set_personal_actions_enabled(service, True)
                self.assertTrue(local_state._personal_actions_enabled(service))
                self.assertEqual(local_state._personal_action_mode(service), "auto-explicit")
                local_state._set_personal_action_mode(service, "preview")
                self.assertEqual(local_state._personal_action_mode(service), "preview")
                local_state._set_personal_actions_enabled(service, False)
                self.assertFalse(local_state._personal_actions_enabled(service))

    def test_explicit_mode_rejects_ambiguity_attendees_recurrence_work_and_send(self) -> None:
        import jarvis_local_state as local_state

        source = (ROOT / "scripts" / "jarvis_local_state.py").read_text()
        self.assertIn("personal_action_explicit", source)
        for blocked in ("invite ", "attendee", "recurring", "work calendar", "send the email"):
            self.assertIn(blocked, source)
        self.assertIn('str(value.get("context") or "") != "personal"', source)

    def test_canonical_action_turn_requires_existing_jarvis_owned_session(self) -> None:
        import jarvis_local_state as local_state

        class FakeDB:
            def __init__(self, source: str = "desktop") -> None:
                self.source = source
                self.appended = None
                self.closed = False

            def get_session(self, session_id: str) -> dict:
                return {"id": session_id, "source": self.source}

            def append_messages_batch(self, session_id: str, messages: list[dict]) -> None:
                self.appended = (session_id, messages)

            def close(self) -> None:
                self.closed = True

        database = FakeDB()
        self.assertTrue(local_state._append_canonical_conversation(
            "jarvis_personal_0123456789abcdef",
            "Create an unsent draft",
            "I created the unsent draft.",
            db_factory=lambda: database,
        ))
        self.assertEqual("jarvis_personal_0123456789abcdef", database.appended[0])
        self.assertEqual(["user", "assistant"], [item["role"] for item in database.appended[1]])
        self.assertTrue(database.closed)

        with self.assertRaises(PermissionError):
            local_state._append_canonical_conversation(
                "not-jarvis", "request", "answer", db_factory=lambda: FakeDB()
            )
        with self.assertRaises(PermissionError):
            local_state._append_canonical_conversation(
                "jarvis_personal_0123456789abcdef",
                "request",
                "answer",
                db_factory=lambda: FakeDB("another_client"),
            )

    def test_conversation_controls_are_recoverable_and_jarvis_owned(self) -> None:
        import jarvis_local_state as local_state

        class FakeDB:
            def __init__(self) -> None:
                self.actions: list[tuple] = []
                self.closed = False

            def get_session(self, session_id: str) -> dict | None:
                source = "another_client" if session_id.endswith("foreign") else "desktop"
                return {"id": session_id, "source": source}

            def set_session_title(self, session_id: str, title: str) -> bool:
                self.actions.append(("rename", session_id, title)); return True

            def set_session_pinned(self, session_id: str, value: bool) -> bool:
                self.actions.append(("pin", session_id, value)); return True

            def set_session_archived(self, session_id: str, value: bool) -> bool:
                self.actions.append(("archive", session_id, value)); return True

            def close(self) -> None:
                self.closed = True

        database = FakeDB()
        with patch.object(local_state, "_canonical_session_db", return_value=database):
            result = local_state.conversation_control(None, {
                "sessionId": "jarvis_personal_0123456789abcdef", "action": "rename", "title": "Daily review",
            })
        self.assertTrue(result["recoverable"])
        self.assertEqual([("rename", "jarvis_personal_0123456789abcdef", "Daily review")], database.actions)
        self.assertTrue(database.closed)

        with patch.object(local_state, "_canonical_session_db", return_value=FakeDB()):
            with self.assertRaises(PermissionError):
                local_state.conversation_control(None, {
                    "sessionId": "jarvis_personal_foreign", "action": "archive",
                })
        with patch.object(local_state, "_canonical_session_db", return_value=FakeDB()):
            with self.assertRaises(PermissionError):
                local_state.conversation_control(None, {
                    "sessionId": "jarvis_personal_0123456789abcdef", "action": "delete",
                })

    def test_governed_turn_persists_only_owner_request_and_final_answer(self) -> None:
        import jarvis_local_state as local_state

        class FakeDB:
            def __init__(self) -> None:
                self.rows: list[dict] = []
                self.closed = False

            def get_session(self, session_id: str) -> dict:
                return {"id": session_id, "source": "desktop", "message_count": len(self.rows)}

            def get_messages(self, _session_id: str, **_kwargs: object) -> list[dict]:
                return list(self.rows)

            def append_messages_batch(self, _session_id: str, messages: list[dict]) -> int:
                self.rows.extend(messages); return len(messages)

            def close(self) -> None:
                self.closed = True

        database = FakeDB()
        session_id = "jarvis_personal_0123456789abcdef"
        with patch.object(local_state, "_canonical_session_db", return_value=database):
            first = local_state.conversation_turn_begin(None, {
                "sessionId": session_id, "turnId": "turn-123", "context": "personal",
                "ownerRequest": "Review this security decision",
            })
        with patch.object(local_state, "_canonical_session_db", return_value=database):
            duplicate = local_state.conversation_turn_begin(None, {
                "sessionId": session_id, "turnId": "turn-123", "context": "personal",
                "ownerRequest": "Review this security decision",
            })
        with patch.object(local_state, "_canonical_session_db", return_value=database):
            finished = local_state.conversation_turn_finish(None, {
                "sessionId": session_id, "turnId": "turn-123", "context": "personal",
                "route": "review", "assistantMessage": "Final reviewed answer.",
                "progress": ["Pro completed", "Terra review completed"],
            })
        with patch.object(local_state, "_canonical_session_db", return_value=database):
            final_duplicate = local_state.conversation_turn_finish(None, {
                "sessionId": session_id, "turnId": "turn-123", "context": "personal",
                "route": "review", "assistantMessage": "Final reviewed answer.",
                "progress": ["Pro completed", "Terra review completed"],
            })
        self.assertFalse(first["idempotent"])
        self.assertTrue(duplicate["idempotent"])
        self.assertFalse(finished["idempotent"])
        self.assertTrue(final_duplicate["idempotent"])
        self.assertEqual(["user", "assistant"], [row["role"] for row in database.rows])
        self.assertEqual("Final reviewed answer.", database.rows[-1]["content"])
        self.assertNotIn("ORIGINAL REQUEST", " ".join(row["content"] for row in database.rows))
        self.assertTrue(database.rows[-1]["display_metadata"]["review_harness_isolated"])
        self.assertTrue(database.closed)

    def test_conversation_list_filters_foreign_rows(self) -> None:
        import jarvis_local_state as local_state

        class FakeDB:
            def list_sessions_rich(self, **_kwargs: object) -> list[dict]:
                return [
                    {"id": "jarvis_personal_1", "source": "desktop", "title": "Keep", "archived": 0, "pinned": 1},
                    {"id": "other_1", "source": "another_client", "title": "Private foreign row"},
                ]

            def close(self) -> None:
                pass

        with patch.object(local_state, "_canonical_session_db", return_value=FakeDB()):
            result = local_state.conversation_list(None, {"includeArchived": True})
        self.assertEqual(["jarvis_personal_1"], [row["id"] for row in result["data"]])


if __name__ == "__main__":
    unittest.main()
