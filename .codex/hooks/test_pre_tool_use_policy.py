#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".codex/hooks/pre_tool_use_policy.py"


def run(tool: str, tool_input: dict, cwd: Path = ROOT) -> tuple[bool, str]:
    payload = {
        "session_id": "test",
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "permission_mode": "bypassPermissions",
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"Hook crashed: {proc.stderr}")
    text = proc.stdout.strip()
    if not text:
        return True, ""
    data = json.loads(text)
    output = data.get("hookSpecificOutput", {})
    return output.get("permissionDecision") != "deny", output.get("permissionDecisionReason", "")


def assert_allow(tool: str, tool_input: dict) -> None:
    allowed, reason = run(tool, tool_input)
    assert allowed, f"Expected allow for {tool} {tool_input}, got: {reason}"


def assert_deny(tool: str, tool_input: dict) -> None:
    allowed, reason = run(tool, tool_input)
    assert not allowed and reason, f"Expected deny for {tool} {tool_input}"


def main() -> None:
    assert_allow("Bash", {"command": "pwd && git status --short"})
    assert_allow("Bash", {"command": "scripts/preflight_safety.sh"})
    assert_allow("Bash", {"command": "scripts/safe_git_push.sh origin"})
    assert_deny("Bash", {"command": "rm notes.txt"})
    assert_deny("Bash", {"command": "python3 -c 'import os; os.remove(\"notes.txt\")'"})
    assert_deny("Bash", {"command": "git push origin main"})
    assert_deny("Bash", {"command": "gh repo create moonishaider/other --private"})
    assert_deny("Bash", {"command": "sudo brew install something"})
    assert_deny("Bash", {"command": "cp file.txt ~/Desktop/file.txt"})
    assert_allow("apply_patch", {"command": "*** Begin Patch\n*** Add File: implementation/test.md\n+ok\n*** End Patch"})
    assert_deny("apply_patch", {"command": "*** Begin Patch\n*** Delete File: README.md\n*** End Patch"})
    assert_allow("apply_patch", {"command": "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-x\n+y\n*** End Patch"})
    assert_deny("mcp__slack__send_message", {"channel": "x", "text": "y"})
    assert_allow("mcp__github__get_file_contents", {"owner": "moonishaider", "repo": "x"})
    assert_deny("computer_use", {"action": "click"})
    print("PreToolUse hook tests: OK")


if __name__ == "__main__":
    main()
