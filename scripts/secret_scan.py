#!/usr/bin/env python3
"""Scan versionable project files for credential-shaped content."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hermes_attention.security import SECRET_PATTERNS  # noqa: E402


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    findings: list[str] = []
    for raw_name in result.stdout.split(b"\0"):
        if not raw_name:
            continue
        relative = raw_name.decode("utf-8", errors="replace")
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            findings.append(relative)
    if findings:
        print("credential-shaped content found in: " + ", ".join(sorted(findings)))
        return 1
    print("Secret scan passed; no configured credential patterns matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
