"""Content-boundary security checks and log-safe redaction."""

from __future__ import annotations

import re


SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all |the )?(?:previous|prior|system) instructions", re.I),
    re.compile(r"reveal (?:the )?(?:system prompt|credentials|secrets)", re.I),
    re.compile(r"(?:run|execute) (?:this )?(?:command|script)", re.I),
    re.compile(r"disable (?:the )?(?:policy|guardrail|safety)", re.I),
]


def redact_secrets(text: str) -> tuple[str, int]:
    redacted = text
    count = 0
    for pattern in SECRET_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED_SECRET]", redacted)
        count += replacements
    return redacted, count


def detect_prompt_injection(text: str) -> list[str]:
    return [pattern.pattern for pattern in INJECTION_PATTERNS if pattern.search(text)]
