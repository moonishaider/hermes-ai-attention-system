# Prompt 8 live product truth

Date: 2026-08-23 (Asia/Karachi)

## Verified baseline and rollback

- Repository: private `moonishaider/hermes-ai-attention-system`, branch `main`, baseline `f3e7c37`.
- Original installed application: `/Applications/Jarvis.app`, bundle `com.moonishaider.jarvis`, version `0.1.0`; deep strict signature verification passed before Prompt 8 changes.
- Backend: Jarvis launches the existing Hermes gateway and project runtime; the user does not need the old Hermes application open.
- Database: `~/.hermes/jarvis-runtime/runtime-data/hermes_attention.sqlite3`; pre-change backup passed SQLite integrity checking.
- Initial app binary SHA-256: `b8449a4ef1b4e7d9759c369483cb6030079662d12fdbe23c90f7197bd48c0a10`.
- Source rollback tag: `prompt8-pre-hardening-20260823` at `f3e7c37`.
- Pre-change app, database, Hermes state, and pre-install app backups are retained under the project `backups/` directory and `~/.hermes/backups/`; no original was overwritten as the only copy.

## Prompt 7 claims not carried forward automatically

- “42/42” is historical and does not prove the current installed app.
- Persistent conversations, inferred context, dependable speech finalization, direct routing, and the full Prompt 8 surfaces are implemented, automated-tested, packaged, signed, and installed, but most visible Prompt 8 contract items are not yet owner-accepted.
- The current UI is a capable prototype but too dense and exposes implementation concepts in normal use.

## Calendar/Gmail regression

- Personal grant: connected, refreshable, exact owner-only scopes.
- Root cause: `jarvis.personal_google_actions.mode=off` and capability execution disabled in the live runtime; OAuth itself was not broken.
- Repair applied: enabled the two allowlisted capabilities in `auto-explicit` mode.
- Still blocked: Gmail send, work account writes, attendees/recurrence, generic Slack sending, company/client writes, generic browser/computer control.
- Acceptance remaining: one normal-Chat personal Calendar create then exact Undo, and one normal-Chat unsent Gmail draft, both from the newly packaged installed app.

## Known inspection limitation

The Codex Computer Use capture attempt failed with a macOS ScreenCaptureKit stream error. This is not counted as a product pass or failure. Runtime/API/source checks continue, and visible acceptance will be repeated after packaging.

## Installed Prompt 8 build truth

- Installed path: `/Applications/Jarvis.app`.
- Installed source identity: `af8ee1128ea472ed1a5316eae99b9cc443a70659` (`Accept bounded Codex sync thread alias`).
- Installed binary SHA-256: `ff9f483c1a3bfaaa78340c6710c245714fdc8219d13f3d9c48e3b9d18cd7260f`.
- Signature: ad-hoc signed for this Mac; `codesign --verify --deep --strict` passes. It is intentionally not Apple-notarized, so Gatekeeper assessment is not represented as passing.
- Runtime: one Jarvis process owns one exact Hermes gateway child on private loopback; the runtime plugin matches repository source.
- Database: current runtime database `PRAGMA quick_check` returns `ok`.
- Post-gate backup/restore drill: `backups/prompt8-post-gate-20260823T201116Z.sqlite3` and `backups/prompt8-post-gate-20260823T201116Z-restore-check.sqlite3` are each 66,473,984 bytes, pass `PRAGMA quick_check`, and share SHA-256 `f3ea01f5a17a6ece44c5e53dc5527de6dc9658f0463bbcfabb239f7b36fd8a1e`.
- Personal Google: connected, exact-scope, refreshable, `ready-refreshable`, and `auto-explicit`; Calendar/Gmail-draft capabilities are enabled while Gmail send and Work Google writes remain absent.
- Integrations: all ten reviewed read-only logical integrations are registered, including separate Google, Slack, GitHub, Zoom, Codex, ChatGPT, and Gemini sources.
- Routes: routine/difficult/vision/review remain DeepSeek V4 Flash, DeepSeek V4 Pro, GPT-5.6 Luna, and GPT-5.6 Terra; Sol remains builder-only.
- A minimal direct Flash probe succeeded in 1.373 seconds. A prior `402 Insufficient Balance` entry in the app log is stale historical output, not the current provider state.
- A bounded live Codex incremental sync through the installed compatibility alias read one thread and inserted two new records without printing private content.

## Verified Prompt 8 source gate

The installed Prompt 8 source contains the following reviewed product work:

- canonical Hermes SessionDB conversations with recent-thread switching, search, rename, pin, recoverable archive/restore, immediate active-session persistence, and canonical final-answer persistence;
- isolation of Pro/Terra review-harness prompts from the owner's visible canonical conversation while retaining the owner's request and the final reviewed answer;
- persistent user bubbles, citations, context, progress metadata, and truthful freshness/confidence labels;
- inferred context with a small explicit correction path that does not widen the Action Firewall;
- longer bounded voice capture, recoverable transcript delivery, spoken/display projections, and cleanup of timers, streams, recognition, and speech on unmount;
- primary Today, Chat, Inbox, Projects, and Actions surfaces, with advanced build/automation controls secondary;
- source-backed Today actions, local tasks, meeting follow-up, Project checkpoints, Decisions, Radars, Focus pause/resume, and learned-item review;
- truthful model, connector, budget, token-freshness, personal-action, and runtime diagnostics with only bounded reviewed repairs;
- fixed-domain evidence opening and public research with no arbitrary browser/computer authority.

The complete post-fix source gate passes 102 Python tests, 20 frontend tests under pinned Node 24, the production TypeScript/Vite build, eight Rust tests under Rust 1.97.1, Rust formatting, warnings-denied Clippy, marked-root preflight, safety controls and negative command checks, secret scan, configuration doctor, and a production npm audit with zero vulnerabilities. Installation is proven, but the installed 48-item acceptance contract remains the completion authority.
