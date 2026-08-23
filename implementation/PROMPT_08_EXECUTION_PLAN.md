# Prompt 8 execution plan

Date: 2026-08-23 (Asia/Karachi)

This is the live implementation plan for `PROMPT_08_JARVIS_PRODUCT_HARDENING_GOAL.md`. The installed `/Applications/Jarvis.app` is product truth; Prompt 7 acceptance records are historical evidence only.

## Safety and rollback

- Marked root: this repository only.
- Baseline commit/tag: `f3e7c3758ec9b8ef4af75d0358343a776451b5e2` / `prompt8-pre-hardening-20260823`.
- App backup: `backups/Jarvis-pre-prompt8-20260823T181429Z.app`.
- Database backup: `backups/prompt8-pre-20260823T181429Z.sqlite3` (`PRAGMA quick_check=ok`).
- Owner configuration backup: `~/.hermes/backups/prompt8-pre-20260823T181429Z` (owner-only permissions).
- No local development server, broad deletion, unrestricted computer control, company/client writes, generic messaging, payments, or credential/scope expansion.

## Milestones

1. **Live truth and action repair** — audit app/runtime/config; restore only personal Calendar create/Undo and unsent Gmail draft; prove send/work writes absent.
2. **Canonical conversation foundation** — persist typed messages, model output, citations, context, progress, timestamps, and thread state in the Hermes-owned runtime; add recent-thread switcher and resume.
3. **Jarvis UX 2.0** — simplify normal navigation to Today, Chat, Inbox, Projects, Actions; infer context with transparent correction; keep advanced controls discoverable but out of the primary path.
4. **Natural voice and speed** — reliable end-of-turn capture, editable transcript/retry, early status, separate spoken/display projections, direct capability routing, interrupt/stop.
5. **Daily intelligence and product surfaces** — Today, Inbox, Project Cockpit, meetings, Focus, Teach Jarvis, Radars, and Decision Journal using accepted evidence boundaries.
6. **Capability health and repair** — truthful connector/action state, token freshness, diagnostic reason, bounded repair for local/re-auth-safe defects.
7. **Installed acceptance** — package signed production app, install, visibly exercise the 48-item contract, run security/negative/regression/resource tests.
8. **Storage and publication** — measure exact footprint, remove only verified redundant Prompt 7 Jarvis artifacts after acceptance, commit coherently, guarded push, leave clean tree.

## Current milestone

Milestone 1 is active. Safety checks passed. The personal Google grant was confirmed connected, exact-scope, and refreshable. The regression cause was a runtime setting of `off`; it has been restored to `auto-explicit` while the generic kill switch and prohibited write surfaces remain unchanged.
