from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/safe_create_private_repo.sh"


class GuardedScriptTests(unittest.TestCase):
    def _run_with_identity(self, identity: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            fake_gh = Path(directory) / "gh"
            fake_gh.write_text(
                "#!/bin/sh\n"
                f"if [ \"$1\" = api ]; then printf '%s\\n' '{identity}'; exit 0; fi\n"
                "if [ \"$1\" = repo ] && [ \"$2\" = view ]; then exit 0; fi\n"
                "exit 99\n",
                encoding="utf-8",
            )
            fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)
            environment = dict(os.environ)
            environment["PATH"] = directory + os.pathsep + environment["PATH"]
            return subprocess.run(
                ["/bin/bash", str(SCRIPT), "hermes-ai-attention-system"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_macos_bash_32_accepts_case_insensitive_expected_identity(self):
        result = self._run_with_identity("MoonisHaider")
        self.assertIn(result.returncode, {4, 5})
        self.assertTrue("origin remote already exists" in result.stderr or "already exists" in result.stderr)
        self.assertNotIn("bad substitution", result.stderr)
        self.assertNotIn("active GitHub identity", result.stderr)

    def test_wrong_identity_still_fails_before_repository_check(self):
        result = self._run_with_identity("someone-else")
        self.assertEqual(3, result.returncode)
        self.assertIn("expected 'moonishaider'", result.stderr)


if __name__ == "__main__":
    unittest.main()
