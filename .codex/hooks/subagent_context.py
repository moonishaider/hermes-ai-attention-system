#!/usr/bin/env python3
"""Inject immutable project-safety context into every Codex subagent."""
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": (
                        "This project runs Codex with Full Access only to avoid repeated approvals. "
                        "Work solely inside the marked Hermes project. Never delete broadly, weaken safety files, "
                        "use sudo/system tools, control the user's browser/computer, expose secrets, perform real "
                        "business-account writes, or modify any inside-success repository. The only GitHub write "
                        "destination is the guarded private moonishaider/hermes-ai-attention-system* repository."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
