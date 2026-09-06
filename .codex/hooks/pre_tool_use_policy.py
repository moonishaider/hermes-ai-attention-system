#!/usr/bin/env python3
"""Deterministic project-local PreToolUse guard for a Full Access Codex build.

This is defence in depth, not an operating-system sandbox. It blocks common
high-impact, outside-project, protected-file, browser/computer-control, and
external-account write operations before a supported Codex tool executes.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable

MARKER = ".hermes-ai-attention-project"
PROTECTED_EXACT = {
    "AGENTS.md",
    "FULL_CONTEXT_HANDOFF.md",
    "MANIFEST.md",
    "CODEX_BOOTSTRAP_PROMPT.md",
    "CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md",
    "CODEX_PROMPT_02_IMPLEMENTATION.md",
    MARKER,
    ".codex/config.toml",
    ".codex/config.toml.example",
    ".codex/hooks.json",
    ".codex/rules/safety.rules",
    ".codex/hooks/pre_tool_use_policy.py",
    ".codex/hooks/subagent_context.py",
    "scripts/preflight_safety.sh",
    "scripts/verify_safety_controls.sh",
    "scripts/test_safety_hook.py",
    "scripts/validate_handoff_package.sh",
    "scripts/verify_github_access.sh",
    "scripts/safe_create_private_repo.sh",
    "scripts/safe_git_push.sh",
}
# Stage B permits reviewed edits to project-owned policy controls. Historical
# handoffs and the marker remain protected; host hook trust is never modified.
MIGRATABLE = {p for p in PROTECTED_EXACT if p.startswith((".codex/", "scripts/"))} | {"AGENTS.md"}
PROTECTED_EXACT -= MIGRATABLE
PROTECTED_PREFIXES = ()
APPROVED_CUA = {"mcp__cua_repl__js", "mcp__cua_repl.js", "mcp__cua_repl__js_reset"}


# Commands that are never needed for this implementation. The guarded GitHub
# wrapper scripts are allowed because their *invocation* does not contain the
# internally blocked command; subprocesses are constrained by those scripts.
BLOCKED_SHELL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|[;&|]\s*)\s*(rm|rmdir|unlink|shred|srm|trash)(\s|$)", re.I), "file deletion"),
    (re.compile(r"\bfind\b[^\n]*(?:-delete|-exec\s+(?:rm|unlink|rmdir))\b", re.I), "destructive find"),
    (re.compile(r"\b(?:python|python3|node|ruby|perl)\b[^\n]*(?:os\.remove|os\.unlink|shutil\.rmtree|Path\([^\n]*\)\.unlink|\.unlink\(|fs\.rm\(|removeSync|rimraf)", re.I), "scripted deletion"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?clean\b", re.I), "git clean"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?reset\b", re.I), "git reset"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?restore\b", re.I), "git restore"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?checkout\s+--\b", re.I), "checkout-based restoration"),
    (re.compile(r"\bgit\s+(?:filter-(?:repo|branch)|rebase)\b", re.I), "Git history rewrite"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?push\b", re.I), "direct git push"),
    (re.compile(r"\bgit\s+branch\s+(?:-D|-d|--delete)\b", re.I), "branch deletion"),
    (re.compile(r"(^|[;&|]\s*)\s*(sudo|doas)\b", re.I), "privilege escalation"),
    (re.compile(r"(^|[;&|]\s*)\s*(dd|mkfs(?:\.\w+)?|newfs|fdisk|parted|mount|umount)\b", re.I), "disk/filesystem administration"),
    (re.compile(r"\bdiskutil\s+(?:eraseDisk|partitionDisk|eraseVolume|deleteVolume)\b", re.I), "destructive disk operation"),
    (re.compile(r"\b(?:chmod|chown)\b[^\n]*(?:-R|--recursive)\b", re.I), "recursive permission/ownership change"),
    (re.compile(r"(^|[;&|]\s*)\s*(shutdown|reboot|halt|poweroff|launchctl|killall|pkill)\b", re.I), "system or broad process control"),
    (re.compile(r"\bdefaults\s+write\b|\bsecurity\s+(?:delete|set-)\b", re.I), "macOS settings or credential mutation"),
    (re.compile(r"\b(?:osascript|automator|shortcuts)\b", re.I), "macOS UI automation"),
    (re.compile(r"(^|[;&|]\s*)\s*open(?:\s|$)", re.I), "opening an application or URL"),
    (re.compile(r"\b(?:ssh|scp|sftp|rsync)\b", re.I), "unbounded remote/cross-filesystem operation"),
    (re.compile(r"\b(?:curl|wget)\b[^\n|;]*(?:\||;)\s*(?:sudo\s+)?(?:sh|bash|zsh|python|python3|node)\b", re.I), "remote content piped into an interpreter"),
    (re.compile(r"\bcurl\b[^\n]*(?:(?:-X|--request)\s*(?:POST|PUT|PATCH|DELETE)|--data(?:-raw|-binary|-urlencode)?\b|--upload-file\b)", re.I), "mutating/upload HTTP request"),
    (re.compile(r"\bgh\s+repo\s+(?:create|delete|archive|edit|rename|transfer|fork)\b", re.I), "direct GitHub repository mutation"),
    (re.compile(r"\bgh\s+(?:issue|pr|release|workflow|secret|variable|label|project|gist)\s+(?:create|edit|delete|close|reopen|merge|run|set|remove|archive|transfer)\b", re.I), "GitHub mutation"),
    (re.compile(r"\bgh\s+api\b[^\n]*(?:(?:-X|--method)\s*(?:POST|PUT|PATCH|DELETE)|(?:-f|--field|--raw-field)\s)", re.I), "mutating GitHub API call"),
    (re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:install|add)\s+(?:-g|--global)\b", re.I), "global JavaScript package installation"),
    (re.compile(r"\b(?:pip|pip3)\s+install\b[^\n]*(?:--user|--break-system-packages)\b", re.I), "user/system Python package installation"),
    (re.compile(r"\b(?:pipx|uv\s+tool)\s+(?:install|uninstall)\b", re.I), "global tool installation"),
    (re.compile(r"\b(?:brew|port)\s+(?:uninstall|cleanup|autoremove)\b", re.I), "system package cleanup/uninstallation"),
]

WRITEISH = re.compile(
    r"\b(?:cp|mv|install|mkdir|touch|tee|truncate|sed\s+-i|perl\s+-pi|unzip|tar|git\s+clone|npm\s+install|pnpm\s+install|yarn\s+install|pip\s+install|python\s+-m\s+pip\s+install)\b|(?:^|[^<])>{1,2}",
    re.I,
)
OUTSIDE_HINT = re.compile(
    r"(?:^|[\s=:'\"])(?:\.\./|~/|\$HOME(?:/|\b)|\$\{HOME\}/|/(?:Users|Volumes|Applications|Library|System|etc|var|tmp)(?:/|\b))"
)
BROWSER_OR_COMPUTER = re.compile(r"browser|chrome|computer|playwright|puppeteer|desktop_control|computer_use", re.I)
EXTERNAL_NAMESPACE = re.compile(r"mcp__|github|slack|gmail|email|calendar|zoom|drive|contacts", re.I)
MUTATING_VERB = re.compile(
    r"(?:^|__|_)(?:send|post|publish|create|update|edit|delete|remove|archive|merge|push|write|upload|move|invite|respond|reply|submit|approve|reject|purchase|checkout|pay|transfer|trigger|dispatch|cancel)(?:$|__|_)",
    re.I,
)


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0)


def locate_root(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return None


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def normalize_target(raw: str, cwd: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw.strip().strip("'\"")))
    path = Path(expanded)
    return path.resolve(strict=False) if path.is_absolute() else (cwd / path).resolve(strict=False)


def relative_target(raw: str, cwd: Path, root: Path) -> str | None:
    try:
        return normalize_target(raw, cwd).relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def is_protected(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized in PROTECTED_EXACT or normalized.startswith(PROTECTED_PREFIXES)


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from iter_strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from iter_strings(child)


def extract_file_targets(tool_input: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    command = tool_input.get("command", tool_input.get("cmd"))
    if isinstance(command, str):
        for line in command.splitlines():
            match = re.match(r"^\*\*\*\s+(?:Add|Update|Delete) File:\s+(.+?)\s*$", line)
            if match:
                targets.append(match.group(1))
    for key in ("path", "file_path", "filename", "target", "destination", "output_path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            targets.append(value)
    return targets


def inspect_file_tool(tool_name: str, tool_input: Any, cwd: Path, root: Path) -> None:
    if isinstance(tool_input, str):
        tool_input = {"command": tool_input}
    if not isinstance(tool_input, dict):
        deny(f"Uninspectable {tool_name} input; file mutation refused.")
    command = tool_input.get("command", tool_input.get("cmd"))
    if isinstance(command, str) and "*** Delete File:" in command:
        deny("File deletion is forbidden; quarantine project-owned files instead.")
    targets = extract_file_targets(tool_input)
    if not targets:
        deny(f"Unable to prove the target path for {tool_name}; write refused.")
    for raw in targets:
        rel = relative_target(raw, cwd, root)
        if rel is None:
            deny(f"File mutation escapes the marked project: {raw}")
        if is_protected(rel):
            deny(f"Protected handoff/safety file cannot be modified: {rel}")


def inspect_shell(tool_input: Any, cwd: Path, root: Path) -> None:
    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("command", tool_input.get("cmd")), str):
        deny("Uninspectable shell command input.")
    command = tool_input.get("command", tool_input.get("cmd"))
    compact = " ".join(command.strip().split())
    if not compact:
        return

    for pattern, label in BLOCKED_SHELL:
        if pattern.search(compact):
            deny(f"Blocked {label}. Use the documented guarded or reversible alternative.")

    # Any write-like shell command that references a protected instruction or
    # guardrail file is denied, regardless of the interpreter used.
    if WRITEISH.search(compact):
        normalized = compact.replace("\\", "/")
        for protected in PROTECTED_EXACT:
            if protected in normalized:
                deny(f"Shell mutation of protected handoff/safety file is forbidden: {protected}")
        if any(prefix in normalized for prefix in PROTECTED_PREFIXES):
            deny("Shell mutation of project hook/rule files is forbidden.")

    # Directory changes must remain inside the marked root.
    for match in re.finditer(r"(?:^|[;&|]\s*)\s*(?:cd|pushd)\s+([^;&|]+)", compact):
        target = match.group(1).strip().strip("'\"")
        if target in {".", "-"}:
            continue
        try:
            resolved = normalize_target(target, cwd)
        except Exception:
            deny("Unable to prove the requested working directory remains inside the project.")
        if not inside(resolved, root):
            deny("Changing the working directory outside the marked project is forbidden.")

    # Parse redirection destinations and deny path escapes/protected writes.
    for raw in re.findall(r"(?:^|\s)(?:>|>>)\s*([^;&|\s]+)", compact):
        rel = relative_target(raw, cwd, root)
        if rel is None:
            deny("Shell redirection outside the marked project is forbidden.")
        if is_protected(rel):
            deny(f"Shell redirection to protected file is forbidden: {rel}")

    # Conservative fallback for obvious outside paths in write-like commands.
    if WRITEISH.search(compact) and OUTSIDE_HINT.search(compact):
        deny("Write-like shell command references a path outside the marked project.")

    # Reject direct writes to inside-success even if a future command evades a
    # more specific GitHub pattern.
    if "inside-success" in compact.lower() and re.search(
        r"\b(?:push|create|edit|delete|merge|close|reopen|set|upload|publish|dispatch|trigger)\b",
        compact,
        re.I,
    ):
        deny("All inside-success GitHub operations are read-only in this build.")


def inspect_external_tool(tool_name: str, tool_input: Any) -> None:
    lowered = tool_name.lower()
    if lowered in APPROVED_CUA:
        # CUA carries opaque JavaScript. This allows the owner-authorized build
        # tool, not arbitrary provider mutation; runtime policy remains separate.
        # Block explicit consequential operations; this is not semantic isolation.
        combined = " ".join(iter_strings(tool_input)).lower()
        if re.search(r"\b(?:checkout|purchase|transfer_funds|send_message|submit_tax|disable_security)\b", combined):
            deny("Consequential browser operation is outside build authority.")
        return
    if BROWSER_OR_COMPUTER.search(lowered):
        deny("Live browser/computer control is blocked during implementation; build and test with mocks.")

    if not EXTERNAL_NAMESPACE.search(lowered):
        return

    combined = " ".join([tool_name, *iter_strings(tool_input)]).lower()
    if MUTATING_VERB.search(combined):
        deny(f"External write-capable tool is blocked during implementation: {tool_name}")

    if isinstance(tool_input, dict):
        method = str(tool_input.get("method") or tool_input.get("http_method") or "").upper()
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            deny(f"Mutating external method is blocked during implementation: {method}")


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception as exc:
        deny(f"Safety hook could not parse tool event: {exc}")

    cwd = Path(str(event.get("cwd") or os.getcwd())).expanduser().resolve()
    root = locate_root(cwd)
    if root is None:
        deny(f"No {MARKER} marker found above the active working directory.")
    if not inside(cwd, root):
        deny(f"Active working directory is outside the marked project: {cwd}")

    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input")
    lowered = tool_name.lower()

    if tool_name == "Bash" or lowered in {"shell", "exec_command", "terminal", "functions.exec_command", "functions__exec_command"}:
        inspect_shell(tool_input, cwd, root)
    elif any(token in lowered for token in ("apply_patch", "write_file", "edit_file", "create_file")) or lowered in {"edit", "write"}:
        inspect_file_tool(tool_name, tool_input, cwd, root)
    else:
        inspect_external_tool(tool_name, tool_input)

    # Empty stdout means allow.


if __name__ == "__main__":
    main()
