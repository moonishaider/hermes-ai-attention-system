# Current Limitations and Fallbacks

Codex must verify these on the implementation date. The purpose is to prevent optimistic assumptions from becoming hidden production dependencies.

## Codex Full Access during implementation

**Limitation:** `danger-full-access` with `approval_policy = "never"` removes Codex's normal filesystem/network containment. Instructions, hooks, rules, Git, and guarded scripts reduce risk but cannot make it equivalent to a sandbox.

**Fallback/control:** a new empty workspace, current backup, immutable project-local PreToolUse hooks and command rules, path-marker preflight, no broad deletion, protected safety files, synthetic data, Git rollback checkpoints, strict GitHub destinations, secret scanning, and immediate stop/report behavior after any unexpected side effect. Re-run the safety tests after Codex updates.

## Personal ChatGPT continuous history

**Limitation:** No assumed supported API for continuously reading the full personal ChatGPT conversation history.

**Primary fallback:** official backfill export plus a one-command local context relay for important future chats.

**Optional fallback:** explicit current-conversation desktop capture, marked experimental and disabled by default.

**Not acceptable:** silent browser scraping presented as reliable synchronization.

## Google Workspace MCP

**Limitation:** Official Workspace MCP availability/scopes may still be Developer Preview or account-dependent.

**Fallback order:** Hermes native Google Workspace skill -> official MCP -> audited narrow connector -> small custom read-only adapter.

**Safety rule:** do not accept unnecessarily broad OAuth scopes.

## Slack write restriction

**Limitation:** A general Slack integration may expose `chat:write` or broader tools.

**Fallback:** separate read-only source connection and a dedicated fixed-channel daily-report publisher holding narrow authority.

## Zoom access and meeting relevance

**Limitation:** Results depend on account permissions, recording ownership, retention, and MCP/API capabilities.

**Fallback:** query accessible recordings/transcripts by group/date/owner and clearly report unavailable meetings. Never claim complete departmental awareness when source coverage is incomplete.

## Existing Chrome profiles

**Limitation:** Reusing signed-in profiles increases consequence if the wrong profile/account is selected.

**Fallback/control:** explicit profile mapping, account/domain display, side-effect preview, mixed/unknown block, and API/MCP preference for structured work actions.

## Hermes feature/API changes

**Limitation:** Hermes is rapidly evolving; plugin, memory, toolset, and Desktop extension details may change.

**Fallback:** pin a stable version, maintain adapter boundaries, record capability matrix, and avoid depending on the main branch without a migration/rollback test.

## Model availability and pricing

**Limitation:** Model names, prices, context limits, tool support, and performance can change.

**Fallback:** configurable routing, provider capability detection, current official verification, fallback model classes, and an evaluation harness. Preserve the approved baseline until evidence supports a change.

## 8 GB Mac performance

**Limitation:** Chrome, Codex, Hermes Desktop, and other work can create swap pressure even with API models.

**Fallback:** cloud STT, bounded caches/concurrency, lazy specialist loading, no local LLM/Postgres/vector service, and measured resource budgets. Do not lower answer quality merely to avoid a small amount of memory use.

## Fully autonomous safety

**Limitation:** Approval systems and prompt-injection defenses reduce risk but do not make unrestricted autonomy safe.

**Fallback:** tool removal, least-privilege credentials, separate executor, exact previews, action classes, manual A4 actions, idempotency, audit, and kill switch.

## 24/7 availability

**Limitation:** A local Mac cannot collect while asleep/offline.

**Fallback:** measure missed value first; then move only light read-only scheduling/collection to a CPU VPS. Keep voice, screen, browser cookies, and computer control local.
