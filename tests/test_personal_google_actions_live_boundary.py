from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

import unittest

from hermes_attention.personal_google_action_oauth import (
    PERSONAL_ACTION_SCOPES, PersonalGoogleActionTokenManager,
)
from hermes_attention.personal_google_actions import PersonalGoogleActionTransport
from hermes_attention.storage import Store

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


if __name__ == "__main__":
    unittest.main()
