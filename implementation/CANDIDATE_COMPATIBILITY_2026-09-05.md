# Personal-assistant candidate compatibility — 5 September 2026

This engineering record now includes guarded local candidate activations. The
isolated interpreter is installed, live databases and credentials were preserved,
and real packaged checks cover chat, documents, reversible personal actions and
selected workspace flows. These checks do not establish all milestone acceptance
or macOS permission continuity. Detailed receipts remain private and Git-excluded.

## Compatibility verified

| Area | Evidence | Limit |
|---|---|---|
| Builder | Project configuration selects `gpt-6-astra`; builder authority remains separate from runtime grants. | Configuration is not a runtime provider acceptance test. |
| Hermes | Reviewed installed source reports 0.20.0 and supports Python `>=3.11,<3.14`. Its existing source modifications, including connection-liveness handling, are preserved. | The vendor environment is not upgraded in place. |
| Candidate interpreter | Isolated Python 3.12.14 / SQLite 3.53.1; dependency consistency check passes. Canonical and attention database copies pass integrity checks and restore comparison. | Tests used consistent copies; activation must preserve live databases and credentials. |
| Python dependencies | Core, MCP and speech dependencies follow the reviewed Hermes source lock. OpenAI SDK remains 2.24.0. Document pins: pypdf 6.10.0, python-docx 1.2.0, openpyxl 3.1.5, reportlab 4.4.9, Pillow 12.3.0, pypdfium2 5.13.0. | No claim that newer packages are automatically compatible; version selection requires review. |
| Gateway | Candidate imports native gateway and database modules; the actual API adapter starts in an isolated synthetic home, answers a loopback health request and shuts down. Outbound connections are denied during this proof. | This is not authenticated provider or complete application lifecycle acceptance. |
| Runtime models | Configured runtime routing retains Flash, Pro, Luna and Terra roles. | Builder configuration does not grant runtime model access; packaged acceptance is separate. |
| Computer use | Official Cua Driver 0.23.2 release checksum and app signature verified. The actual Hermes adapter reaches its standard-mode private service. | Window discovery reports pending macOS Accessibility or Screen Recording permission. Builder computer tools do not establish runtime permission. |
| Frontend installation | Only compiled static assets enter the companion root. File hashes, supported types, bounds and path checks prevent copying the whole frontend workspace. | The companion remains subject to its separate authenticated private-ingress configuration. |

The candidate environment must be created directly at its permanent versioned
runtime path. Copying an existing virtual environment would retain stale absolute
shebangs. Activation binds the reviewed code, compiled assets, dependency snapshot,
driver and app hashes, and uses an owner-only interpreter selection file.

Primary references: [Hermes computer use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use),
[Cua installation](https://cua.ai/docs/how-to-guides/driver/install), and the
[pinned Cua release](https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.23.2).
Exact private compatibility receipts remain excluded from Git.

## Current policy precedence

The current authorization section in [AGENTS.md](../AGENTS.md) takes precedence
over historical prototype instructions only within its explicit scope. This
permits reviewed project-policy maintenance, scoped browser/computer setup and
owned app/runtime installation. It does not transfer builder privileges to Jarvis.

The publication destination is the existing **public** project repository.
Historical descriptions of private publication or an unrestricted personal
namespace are superseded. Guarded publication requires its exact remote,
visibility, branch and reviewed commit, with committed-blob scanning. Source data,
private specifications, credentials, detailed audits and screenshots are excluded.

Historical blanket prohibitions on all learning edits and personal actions are
replaced by specific native owner decisions, versioned changes and task grants.
Uncertain learning remains staged; native pending proposals retain exact-item
review. Company writes, sends, payments, scope expansion and consequential browser
submission remain outside general task grants. Standard driver operation does not
approve OS permissions or bypass task-level action controls. Hooks remain
compensating checks, not an operating-system sandbox.

## Activation and rollback limits

Activation has not been claimed in this record. Reviewed helpers preserve the
old app, named runtime code and private configuration; failed or replaced files
are retained in a private quarantine. Rollback refuses to overwrite newer work
and never replaces operational databases or credentials. The installer does not
upgrade the vendor environment or modify global security policy.

An ad-hoc app signature can change its designated code requirement when the binary
changes. Keeping the same bundle identifier does **not** prove that macOS grants
will survive. Recheck the installed app and signed driver after replacement;
normal owner consent may be required. No TCC reset, grant injection, unrestricted
driver mode or automatic approval is part of the candidate.
