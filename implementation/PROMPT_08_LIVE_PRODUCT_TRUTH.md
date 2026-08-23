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
- Persistent conversations, inferred context, dependable speech finalization, direct routing, and the full Prompt 8 surfaces are not yet accepted.
- The current UI is a capable prototype but too dense and exposes implementation concepts in normal use.

## Calendar/Gmail regression

- Personal grant: connected, refreshable, exact owner-only scopes.
- Root cause: `jarvis.personal_google_actions.mode=off` and capability execution disabled in the live runtime; OAuth itself was not broken.
- Repair applied: enabled the two allowlisted capabilities in `auto-explicit` mode.
- Still blocked: Gmail send, work account writes, attendees/recurrence, generic Slack sending, company/client writes, generic browser/computer control.
- Acceptance remaining: one normal-Chat personal Calendar create then exact Undo, and one normal-Chat unsent Gmail draft, both from the newly packaged installed app.

## Known inspection limitation

The Codex Computer Use capture attempt failed with a macOS ScreenCaptureKit stream error. This is not counted as a product pass or failure. Runtime/API/source checks continue, and visible acceptance will be repeated after packaging.
