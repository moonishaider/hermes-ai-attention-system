#!/usr/bin/env python3
"""Non-destructive tests for the project PreToolUse hook."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".codex" / "hooks" / "pre_tool_use_policy.py"


def run(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    payload = {"cwd": str(ROOT), "tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )
    if proc.returncode != 0:
        return False, f"hook process failed: {proc.stderr.strip()}"
    if not proc.stdout.strip():
        return True, "allowed"
    data = json.loads(proc.stdout)
    output = data.get("hookSpecificOutput", {})
    denied = output.get("permissionDecision") == "deny"
    return not denied, output.get("permissionDecisionReason") or output.get("additionalContext") or "allowed"


def expect(name: str, expected_allow: bool, tool_name: str, tool_input: dict) -> None:
    allowed, reason = run(tool_name, tool_input)
    if allowed != expected_allow:
        raise AssertionError(f"{name}: expected allow={expected_allow}, got allow={allowed}: {reason}")
    print(f"PASS {name}: {'allowed' if allowed else 'denied'}")


def main() -> int:
    expect("safe pwd", True, "Bash", {"command": "pwd"})
    expect("safe guarded push wrapper", True, "Bash", {"command": "scripts/safe_git_push.sh"})
    expect("recursive delete", False, "Bash", {"command": "rm -rf /"})
    expect("wrapper chaining cannot bypass", False, "Bash", {"command": "scripts/safe_git_push.sh; rm -rf /"})
    expect("direct git push", False, "Bash", {"command": "git push origin main"})
    expect("direct repo creation", False, "Bash", {"command": "gh repo create moonishaider/hermes-ai-attention-system --private"})
    expect("mutating gh api", False, "Bash", {"command": "gh api -X POST repos/moonishaider/example/issues -f title=x"})
    expect("outside cd", False, "Bash", {"command": "cd .. && pwd"})
    expect("outside redirection", False, "Bash", {"command": "echo test > ../outside.txt"})
    expect("absolute outside write", False, "Bash", {"command": "touch /tmp/hermes-test"})
    expect("protected update", False, "apply_patch", {"command": "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-x\n+y\n*** End Patch"})
    expect("file delete", False, "apply_patch", {"command": "*** Begin Patch\n*** Delete File: temporary.txt\n*** End Patch"})
    expect("ordinary project patch", True, "apply_patch", {"command": "*** Begin Patch\n*** Add File: src/example.py\n+print('ok')\n*** End Patch"})
    expect("GitHub read MCP", True, "mcp__github__search_code", {"query": "Hermes"})
    expect("GitHub write MCP", False, "mcp__github__create_issue", {"owner": "moonishaider", "repo": "x", "title": "x"})
    expect("generic GitHub POST", False, "mcp__github__api", {"method": "POST", "path": "/repos/x/y/issues"})
    expect("Slack read", True, "mcp__slack__search_messages", {"query": "daily activity"})
    expect("Slack send", False, "mcp__slack__send_message", {"channel": "x", "text": "x"})
    expect("browser control", False, "computer_use", {"action": "click", "x": 1, "y": 1})
    print("All safety-hook tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
