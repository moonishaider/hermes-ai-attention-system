from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.safe_quarantine_jarvis_artifacts import build_manifest, quarantine_manifest


class Prompt8StorageTests(unittest.TestCase):
    def project(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / ".hermes-ai-attention-project").write_text("test\n", encoding="utf-8")
        target = root / "jarvis" / "dist"
        target.mkdir(parents=True)
        (target / "index.html").write_text("reproducible\n", encoding="utf-8")
        return temporary, root

    def test_manifest_is_exact_allowlisted_and_metadata_hashed(self) -> None:
        temporary, root = self.project()
        with temporary:
            manifest = build_manifest(root, ["frontend-dist"], "2026-08-24T00:00:00+00:00")
            self.assertEqual(manifest["operation"], "project-local-quarantine-only")
            self.assertFalse(manifest["deletion_supported"])
            self.assertEqual(manifest["entries"][0]["path"], "jarvis/dist")
            self.assertEqual(len(manifest["entries"][0]["metadata_sha256"]), 64)

    def test_non_allowlisted_and_symlink_candidates_fail_closed(self) -> None:
        temporary, root = self.project()
        with temporary:
            with self.assertRaises(PermissionError):
                build_manifest(root, ["runtime-data"])
            (root / "jarvis" / "dist" / "escape").symlink_to(root / ".hermes-ai-attention-project")
            with self.assertRaises(PermissionError):
                build_manifest(root, ["frontend-dist"])

    def test_internal_symlink_is_hashed_without_following_it(self) -> None:
        temporary, root = self.project()
        with temporary:
            target = root / "jarvis" / "dist"
            (target / "entry").symlink_to("index.html")
            manifest = build_manifest(root, ["frontend-dist"])
            self.assertEqual(manifest["entries"][0]["object_count"], 3)
            self.assertEqual(len(manifest["entries"][0]["metadata_sha256"]), 64)

    def test_changed_candidate_cannot_be_quarantined(self) -> None:
        temporary, root = self.project()
        with temporary:
            manifest = build_manifest(root, ["frontend-dist"])
            (root / "jarvis" / "dist" / "index.html").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                quarantine_manifest(root, manifest, dry_run=False)

    def test_dry_run_is_noop_and_quarantine_is_recoverable(self) -> None:
        temporary, root = self.project()
        with temporary:
            manifest = build_manifest(root, ["frontend-dist"])
            dry = quarantine_manifest(root, json.loads(json.dumps(manifest)), dry_run=True)
            self.assertEqual(dry["freed_bytes"], 0)
            self.assertTrue((root / "jarvis" / "dist" / "index.html").is_file())
            result = quarantine_manifest(root, manifest, dry_run=False)
            self.assertTrue(result["recoverable"])
            self.assertEqual(result["freed_bytes"], 0)
            destination = root / ".workspace-quarantine" / f"prompt8-storage-{manifest['manifest_id']}" / "jarvis" / "dist" / "index.html"
            self.assertTrue(destination.is_file())
            self.assertFalse((root / "jarvis" / "dist").exists())


if __name__ == "__main__":
    unittest.main()
