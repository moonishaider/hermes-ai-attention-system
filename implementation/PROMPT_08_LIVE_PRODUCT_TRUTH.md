# Prompt 8 live product truth

Date: 2026-08-23 (Asia/Karachi)

## Verified baseline

- Repository: private `moonishaider/hermes-ai-attention-system`, branch `main`, baseline `f3e7c37`.
- Installed application: `/Applications/Jarvis.app`, bundle `com.moonishaider.jarvis`, version `0.1.0`; deep strict signature verification passed before Prompt 8 changes.
- Backend: Jarvis launches the existing Hermes gateway and project runtime; the user does not need the old Hermes application open.
- Database: `~/.hermes/jarvis-runtime/runtime-data/hermes_attention.sqlite3`; pre-change backup passed SQLite integrity checking.
- Initial app binary SHA-256: `b8449a4ef1b4e7d9759c369483cb6030079662d12fdbe23c90f7197bd48c0a10`.

## Prompt 7 claims not carried forward automatically

- “42/42” is historical and does not prove the current installed app.
- Persistent conversations, inferred context, dependable speech finalization, direct routing, and the full Prompt 8 surfaces are now implemented and automated-tested in source, but are not yet accepted in the installed application.
- The current UI is a capable prototype but too dense and exposes implementation concepts in normal use.

## Calendar/Gmail regression

- Personal grant: connected, refreshable, exact owner-only scopes.
- Root cause: `jarvis.personal_google_actions.mode=off` and capability execution disabled in the live runtime; OAuth itself was not broken.
- Repair applied: enabled the two allowlisted capabilities in `auto-explicit` mode.
- Still blocked: Gmail send, work account writes, attendees/recurrence, generic Slack sending, company/client writes, generic browser/computer control.
- Acceptance remaining: one normal-Chat personal Calendar create then exact Undo, and one normal-Chat unsent Gmail draft, both from the newly packaged installed app.

## Known inspection limitation

The Codex Computer Use capture attempt failed with a macOS ScreenCaptureKit stream error. This is not counted as a product pass or failure. Runtime/API/source checks continue, and visible acceptance will be repeated after packaging.

## Verified Prompt 8 source gate

The current uncommitted source contains the following reviewed product work:

- canonical Hermes SessionDB conversations with recent-thread switching, search, rename, pin, recoverable archive/restore, immediate active-session persistence, and canonical final-answer persistence;
- isolation of Pro/Terra review-harness prompts from the owner's visible canonical conversation while retaining the owner's request and the final reviewed answer;
- persistent user bubbles, citations, context, progress metadata, and truthful freshness/confidence labels;
- inferred context with a small explicit correction path that does not widen the Action Firewall;
- longer bounded voice capture, recoverable transcript delivery, spoken/display projections, and cleanup of timers, streams, recognition, and speech on unmount;
- primary Today, Chat, Inbox, Projects, and Actions surfaces, with advanced build/automation controls secondary;
- source-backed Today actions, local tasks, meeting follow-up, Project checkpoints, Decisions, Radars, Focus pause/resume, and learned-item review;
- truthful model, connector, budget, token-freshness, personal-action, and runtime diagnostics with only bounded reviewed repairs;
- fixed-domain evidence opening and public research with no arbitrary browser/computer authority.

The source gate passes 101 Python tests, 20 frontend tests, the production TypeScript/Vite build, eight Rust tests, Rust formatting, warnings-denied Clippy, marked-root preflight, safety controls and negative command checks, secret scan, configuration doctor, and a production npm audit with zero vulnerabilities. The installed app remains the accepted Prompt 7 build until the exact Prompt 8 commit is packaged, signed, installed, and visibly exercised.
