from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from hermes_attention.service import AttentionService
from hermes_attention.zoom_acceptance_import import import_zoom_acceptance


def _payload(*, system: str = "zoom_readonly") -> dict:
    reference = "opaque-meeting-reference"
    return {
        "case_id": "zoom_recent_meeting",
        "status_checked": True,
        "writes_disabled": True,
        "success": True,
        "answer": "Private accepted answer",
        "claims": [{
            "claim": "One authorized meeting asset is available.",
            "source_refs": [reference],
            "confidence": 0.99,
            "label_state": "confirmed",
        }],
        "sources": [{
            "system": system,
            "connection_id": "zoom_readonly:search_meetings",
            "ref": reference,
            "date": "2026-08-03",
            "context": "inside-success",
        }],
        "leakage_detected": False,
        "failure_reason": None,
    }


class ZoomAcceptanceImportTests(unittest.TestCase):
    def test_import_is_private_idempotent_and_provenance_linked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            private = tmp_path / "private"
            private.mkdir()
            response = private / "zoom.response.json"
            response.write_text(json.dumps(_payload()) + "\n", encoding="utf-8")
            service = AttentionService(database=tmp_path / "state.sqlite3")
            try:
                first = import_zoom_acceptance(service, response, private_root=private)
                second = import_zoom_acceptance(service, response, private_root=private)
                self.assertEqual(first["inserted_count"], 1)
                self.assertTrue(first["ledger_created"])
                self.assertEqual(second["inserted_count"], 0)
                self.assertFalse(second["ledger_created"])
                evidence = service.store.connection.execute(
                    "SELECT title,content,provenance_json,contexts_json FROM evidence"
                ).fetchone()
                provenance = json.loads(evidence["provenance_json"])
                self.assertEqual(evidence["title"], "Authorized Zoom meeting evidence — 2026-08-03")
                self.assertEqual(evidence["content"], "One authorized meeting asset is available.")
                self.assertEqual(provenance["source_system"], "zoom")
                self.assertEqual(provenance["connection_id"], "zoom_readonly")
                self.assertIsNone(provenance["uri"])
                self.assertNotIn("opaque-meeting-reference", json.dumps(provenance))
                self.assertEqual(json.loads(evidence["contexts_json"])[0]["context_id"], "inside-success")
                self.assertEqual(service.store.connection.execute("SELECT count(*) FROM ledger_sources").fetchone()[0], 1)
            finally:
                service.close()

    def test_import_rejects_non_zoom_or_outside_private_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            private = tmp_path / "private"
            private.mkdir()
            outside = tmp_path / "outside.json"
            outside.write_text(json.dumps(_payload()) + "\n", encoding="utf-8")
            response = private / "zoom.response.json"
            response.write_text(json.dumps(_payload(system="slack")) + "\n", encoding="utf-8")
            service = AttentionService(database=tmp_path / "state.sqlite3")
            try:
                with self.assertRaises(PermissionError):
                    import_zoom_acceptance(service, outside, private_root=private)
                with self.assertRaises((PermissionError, ValueError)):
                    import_zoom_acceptance(service, response, private_root=private)
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
