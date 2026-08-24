# Prompt 8 live product truth

Date: 2026-08-25 (Asia/Karachi)

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
- Installed source identity: `433484b2f188cc11184b326b19769ff430569d1a` (`Replace TTS recognizer with bounded voice barge-in`).
- Installed binary SHA-256: `4d3d58fbc35108fb8816d397e68d270fe05f09de527f45056542350a2e883f06`.
- Signature: ad-hoc signed for this Mac; `codesign --verify --deep --strict` passes. It is intentionally not Apple-notarized, so Gatekeeper assessment is not represented as passing.
- Runtime: one Jarvis process owns one exact Hermes gateway child on private loopback; the runtime plugin matches repository source byte-for-byte.
- Database: current runtime database `PRAGMA quick_check` returns `ok`.
- Final non-overwriting backups: `backups/prompt8-final-433484b-20260825T0210.sqlite3` is 62,468,096 bytes with SHA-256 `8e6b7cb3916dd4ba19fd2aad37c10bfde85045bf85e9eb4c3f34c63f3915ad2d`; `backups/prompt8-final-runtime-copy-433484b-20260825T0210.sqlite3` is 66,473,984 bytes with SHA-256 `7d10bb000b852bfd07c81d2145e6c67aabe6ac8c5206647f206944d156510713`. Both pass `PRAGMA quick_check`. Current config, SOUL, USER, and state also have an owner-only non-Git backup under `~/.hermes/backups/prompt8-final-433484b-20260825T0210/`.
- Personal Google: connected, exact-scope, refreshable, `ready-refreshable`, and `auto-explicit`; Calendar/Gmail-draft capabilities are enabled while Gmail send and Work Google writes remain absent.
- Installed Personal-action acceptance: one clearly labeled Personal Calendar event was created through the exact native capability and then exactly undone; one clearly labeled unsent Personal Gmail draft was created once. Both actions used canonical `desktop` conversation records, no email was sent, and no company/client account was mutated. A request containing a send phrase failed closed before the accepted unsent-draft request.

### Conversation persistence repair discovered during installed acceptance

An authenticated installed-gateway probe found that Hermes normalizes the unsupported session source `jarvis_desktop` to `api_server`. That made a newly created Jarvis conversation fail the reviewed ownership filter after relaunch. The native client, renderer, and owner-local conversation controls now use Hermes' supported `desktop` source consistently. The exact installed build created a canonical `desktop` thread, persisted one user and one assistant message, passed rename/pin/unpin/archive/unarchive, fully quit with no orphan gateway, relaunched, and recovered the archived two-message thread. Synthetic acceptance threads remain recoverably archived.
- Integrations: all ten reviewed read-only logical integrations are registered, including separate Google, Slack, GitHub, Zoom, Codex, ChatGPT, and Gemini sources.
- Final installed Slack regression: Jarvis used `slack_inside_success_readonly` directly and found recent Inside Success messages. A final bounded two-day probe returned 5,431 characters of evidence without printing private content, reported no truncation, and exposed no write capability. It did not substitute Codex history. Current provider search output includes channel, sender, and timestamp metadata but no durable message IDs/permalinks, which Jarvis reports honestly as source links absent. No Slack message was sent.
- Final installed conversation regression: the active canonical `desktop` thread restores after full relaunch; bounded `conversation_history` is injected into follow-ups; visible history retains the owner request and one final Jarvis answer rather than every interim progress bubble. “Say that again” therefore has the prior answer in the same run context.
- Final installed voice repairs: Syed confirmed natural finish auto-submits after silence and that spoken interruption now stops output immediately. Finalization uses 5.5 seconds after the last changed WebKit recognition hypothesis rather than its unreliable `isFinal` flag; completed delivery clears the transient live transcript. During TTS, the installed `433484b` repair retains one echo-cancelled owner stream and performs only transient local energy detection after calibration. Five sustained frames above the bounded threshold stop speech immediately; all tracks, animation frames, and the audio context are then released. No interruption audio is recorded, transcribed, submitted, or persisted, and the assistant's own spoken word `stop` is never interpreted as a command. macOS may request microphone permission again after an ad-hoc-signed app bundle is replaced; that is an acknowledged packaging-identity limitation.
- Final Zoom regression: live discovery still returned 12 provider tools, but the runtime allowlist exposed exactly `search_meetings`, `get_meeting_assets`, `get_recording_resource`, and `recordings_list`. A metadata-only `recordings_list` smoke passed; provider writes remained excluded and no meeting content was printed.
- Routes: routine/difficult/vision/review remain DeepSeek V4 Flash, DeepSeek V4 Pro, GPT-5.6 Luna, and GPT-5.6 Terra; Sol remains builder-only.
- A minimal direct Flash probe succeeded in 1.373 seconds. A prior `402 Insufficient Balance` entry in the app log is stale historical output, not the current provider state.
- A bounded live Codex incremental sync through the installed compatibility alias read one thread and inserted two new records without printing private content.

### Final installed UI and recovery inspection

- The primary owner path visibly exposes Today, Chat, Inbox, Projects, and Actions; Missions, Radars, Teach Jarvis, Learning, Decisions, Activity, Diagnostics, and Settings remain discoverable secondary surfaces.
- Today rendered current attention, top evidence, waiting/blockers, meeting lifecycle, briefing/resumption, one-shot screen viewing, Focus, and capability health without inventing unavailable Zoom evidence.
- Inbox, Project Cockpit, Mission, Radar, Teach Jarvis, Learning, Decisions, Settings, and Diagnostics all opened in the installed application. The active Project showed its completion contract and Save My Place form; Learning showed one learned profile item plus the advanced graph link.
- The installed voice-recovery diagnostic retained its exact synthetic transcript, exposed Retry/Edit/Discard, and Retry completed once in the same canonical thread with the expected answer. A routine retry did not touch connectors.
- The bounded Repair control refreshed the stale Personal Google access token through the existing refresh grant without changing scopes, tools, accounts, or write authority.
- Guided navigation rendered and then cancelled two exact no-mutation previews: Personal/Profile 1 for `upwork.com`, and Inside Success/Profile 2 for `calendar.google.com`. The second preview required an explicit context correction before it became valid. No browser page was opened.
- Health visibly reported Hermes 0.20.0, the `433484b` build marker, approved model routes without Sol, the exact read/write capability boundaries, all history counts, and the external-action kill switch.
- Hermes SessionDB reports that its bundled SQLite 3.42.0 is below the safe WAL-reset threshold and automatically uses `journal_mode=DELETE`. This is the accepted fail-safe posture for the current bounded single-owner desktop workload; current and backup databases all return `PRAGMA quick_check=ok`. It is a concurrency/performance limitation, not silent corruption or a reason to enable an unsafe journal mode.

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

The complete post-fix source gate passes 110 Python tests, 25 frontend tests under pinned Node 24, the production TypeScript/Vite build, nine Rust tests under Rust 1.97.1, Rust formatting, warnings-denied Clippy, marked-root preflight, safety controls and negative command checks, secret scan, configuration doctor, and a production npm audit with zero vulnerabilities. The reviewed exact-manifest tool was then applied to four allowlisted reproducible build paths only. It moved 18,378,960,151 logical bytes to recoverable project-local quarantine, reported an honest `freed_bytes=0`, and left the installed app, runtime, databases, secrets, histories, memories, final backups, and rollback application intact. Post-quarantine launch, health, signature, database integrity, connector inventory, and credential-mode checks passed. The installed 48-item ledger remains the completion authority and distinguishes visible, installed, automated, and unavailable-real-data evidence.
