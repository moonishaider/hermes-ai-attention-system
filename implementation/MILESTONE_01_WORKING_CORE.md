# Milestone 01 — Working local core and Hermes adapter

**Date:** 2026-08-01
**Baseline:** `b8e8a6e`
**External business writes:** none

## Delivered

- One Hermes project plugin and one assistant personality/context surface.
- Immutable-provenance evidence model, SQLite/FTS retrieval, memory proposals, tasks/open loops, audit, cost usage, and checkpoints.
- Deterministic flexible context classification with personal, Inside Success, Mitchell, mixed, and unknown states.
- Attention ranking, context handoffs, evidenced daily-report drafts, explicit screen request contract, and optional text/status overlay.
- Approved model-role router and monthly warning/hard cost controls.
- Preview/hash/expiry/idempotency/risk/context/profile action controls with external execution disabled and no executor exposed.
- Incremental local Codex JSONL ingestion, confirmed official ChatGPT export import, and explicit structured context relay.
- Registry/template-driven specialists and disabled-by-default external integration registry.
- Two owner-bound GitHub read-only configurations and provenance normalizer.
- Synthetic fixtures, automated unit/integration/security tests, diagnostics, secret scan, backup helper, and manual runbooks.

## Automated evidence

- `13` tests passed with Python 3.11 stdlib `unittest`.
- Configuration doctor: passed.
- Secret scan: passed.
- Git diff whitespace check: passed.
- Negative security tests: connector write names rejected; changed previews rejected; unknown/mixed consequential actions rejected; A4 manual-only; ChatGPT import without confirmation rejected; Hermes plugin has no executor.

## Deliberate deferrals

- Hermes/provider installation and credentialed API smoke tests require Syed’s keys and local configuration review.
- GitHub MCP, Slack, Google, and Zoom OAuth require manual account/consent selection.
- Screen Recording permission and any capture adapter require explicit manual approval; none was requested or used.
- Real-data calibration, voice acceptance, and backup/restore drill require local user interaction.
- External action execution is not part of this milestone.
