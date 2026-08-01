# Milestone 0 — Safe Foundation

**Started:** 2026-08-01
**Baseline commit:** `b8e8a6e`
**Status:** In progress

## Scope

- Requirement IDs: OPS-003–010, GIT-001–003, CDX-001–005.
- Establish safety, compatibility evidence, repository foundation, implementation records, and a testable architecture.
- Exclude real OAuth, API keys, macOS permissions, browser/computer control, live business writes, and real private source ingestion.

## Gate evidence

- Marked-root preflight passed.
- Trusted PreToolUse and SubagentStart hook hashes are persisted.
- Hook and native command-rule tests passed.
- Baseline Git commit created before implementation changes.

## Rollback

The baseline handoff is preserved at commit `b8e8a6e`. No destructive Git restoration is permitted; rollback uses a new branch or targeted reviewed patches.
