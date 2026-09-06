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
                        "Follow the current authorized project build scope in AGENTS.md. "
                        "Selected builder: GPT-6 Astra; runtime billing is separate. Scoped policy migration, "
                        "Jarvis GUI/Chrome testing and reviewed owned-runtime helpers are allowed. "
                        "Keep hooks active and preserve the project marker. No broad deletion, privilege "
                        "escalation, secret exposure, unrelated writes, company writes, unsolicited sends, "
                        "payments or final submissions. Only sanitized publication through the guard to "
                        "the exact PUBLIC moonishaider/hermes-ai-attention-system repository is authorized."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
