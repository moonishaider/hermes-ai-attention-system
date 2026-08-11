# Prompt 7 Execution Plan

**Started:** 12 August 2026

**Goal:** Deliver a packaged Tauri 2 + React/TypeScript `Jarvis.app` as the normal interface to the existing Hermes backend, with adaptive routing, reliable voice, proactive intelligence, bounded personal actions, and bounded computer awareness.

## Gate 0 — Audit and rollback

- Preserve the Prompt 7 specification verbatim and record owner authorization.
- Revalidate marked root, hooks/rules, clean baseline, private remote, versions, installed app/runtime, connectors, model routes, permissions, tests, and resource baseline.
- Back up the runtime database, Hermes configuration/profile/skills state, installed Hermes app, and any state that Jarvis will migrate.
- Create and tag a pre-implementation rollback checkpoint.
- Verify official current Hermes, Tauri, React, TypeScript, Rust/macOS, Google, Zoom, DeepSeek, OpenAI, and Codex interfaces before pinning.

## Gate 1 — Hermes adapter and Jarvis shell

- Create one `HermesBackendAdapter` boundary and narrow loopback-authenticated native command surface.
- Build production-static React/TypeScript UI and minimal Tauri 2 Rust layer with one-instance, tray/menu lifecycle, global shortcuts, health, cancellation, and safe process ownership.
- Provide Now, Work Ledger, Projects, Missions, Radars, Actions, Learning, Capability Studio, Settings, Diagnostics, and compact HUD surfaces.
- Build without `tauri dev`, a Vite dev server, Docker, local LLMs, or a second general daemon.

## Gate 2 — Interaction quality and model governance

- Implement retained dictation, live transcript, idempotent delivery, retry/edit/discard, tap/hold voice modes, natural pause handling, deterministic spoken/display response projection, Stop, barge-in, and typed-quiet behavior.
- Implement deterministic Flash/Pro/Luna/Terra model selection and escalation with route reason, reviewer state, latency, cost, override, and existing budget enforcement. Sol remains builder-only.

## Gate 3 — Proactive intelligence

- Add one incremental provenance-backed Work Ledger with checkpoints and no redundant connector fan-out.
- Derive DLOA, start/end-of-day, pre/post-meeting, absence, urgent, and weekly products from the ledger.
- Add Living Project State, Decision Journal, Missions, Radars, Automation Miner, and dormant Mitchell behavior.

## Gate 4 — Capability Studio and Action Firewall

- Add declarative low-risk capability creation, validation, dry run, activation, disable/archive/undo, and Codex-ready spec generation for code-requiring requests.
- Generalize exact account/context/target/payload/expiry/idempotency/profile/audit/undo controls into the Action Firewall.
- Keep generic Slack sending, company/client writes, checkout, payments, tax/legal submission, credential changes, and destructive actions unavailable.

## Gate 5 — Personal actions, awareness, and Zoom depth

- Add a separate personal Calendar surface for the selected existing calendar and a personal Gmail draft-only surface; work writes stay absent.
- Derive an editable Calendar Style Profile from bounded evidence.
- Add explicit Off/Look now/Focus computer-awareness modes, indicators, allow/deny lists, non-retaining screenshots, Profile 1/Profile 2 boundaries, and preview-before-mutation navigation.
- Audit Zoom account-level read depth and either accept legitimate Tyler-hosted retrieval or record one exact provider/admin blocker.

## Gate 6 — Packaging and visible acceptance

- Run unit, integration, Rust, frontend, security, policy, backup/restore, resource, packaging, and regression checks.
- Package, locally sign, install, and launch `/Applications/Jarvis.app` without Terminal or stock Hermes UI.
- Exercise the 42-item visible acceptance ledger with private-safe evidence; do not substitute scaffolding or synthetic tests for visible claims.
- Update authoritative state, startup guide, architecture, permission matrix, threat model, resource/cost, rollback/uninstall, and acceptance records.
- Finish with a clean tree and guarded private publication.

