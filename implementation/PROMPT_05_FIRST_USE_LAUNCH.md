# Prompt 5 First-Use Launch

Checked: 4 August 2026

## Decision

The accepted architecture did not need rebuilding. Hermes 0.19.1 provided a real terminal chat UI but no installed native `.app` and no existing double-click project launcher. The smallest safe packaging change was therefore one executable `Launch Hermes.command` inside the marked project. It delegates all behavior to `scripts/launch_daily_hermes.sh`; it does not copy launch logic or create a server, daemon, login item, service, launch agent, or persistent background process.

The audit also found that accepted one-shot screen understanding was not reachable end to end from normal chat: the exposed tool created only a request record, while the reviewed capture/Luna path lived in an acceptance script. A separate `hermes_attention_view_screen_once` tool now connects the same visible selection-only adapter to Luna. The user must still select a region in Apple's UI or cancel. The tool retains no pixels, redacts credential-shaped response text, never follows visible instructions, and provides no mouse, keyboard, Accessibility, or continuous-capture capability.

## Real first-use verification

- Canonical launch refreshed Google, refreshed Zoom on connection, printed credential-safe health, started the overlay, and reached the Hermes v0.19.1 prompt.
- The real assistant called `hermes_attention_status` and reported external writes disabled, kill switch active, and generic Slack sender absent.
- `/voice on` enabled voice mode with TTS and displayed `Control+B` recording guidance; `/voice off` disabled it and `/exit` closed normally.
- The live Hermes tool search found `hermes_attention_view_screen_once`; capture was deliberately not invoked because Prompt 4 already completed the supervised real screen test and Prompt 5 forbids redundant broad acceptance.
- Existing overlay acceptance remains authoritative for Cancel, Mute/Unmute, and Dismiss; deterministic tests were rerun. Codex did not drive the macOS buttons because `AGENTS.md` forbids build-time computer control.
- The double-click wrapper was syntax-checked, executable, and exercised with the canonical launch path.

## One representative daily task

Exactly one multi-source project-resumption case ran over 26 July–4 August:

| Result | Evidence |
|---|---|
| Accepted | 7/7 claims cited |
| Provenance | 18/18 claim references resolved across 15 sources |
| Labels | 5 confirmed, 1 inferred, 1 uncertain |
| Context | Personal plus genuine unknown retained |
| Safety | Status checked; writes disabled; no reported leakage |
| Route | DeepSeek V4 Flash |
| Latency | 178.9 seconds |
| Estimated cost | $0.01115 |

The task succeeded but used most of the 180-second bound. No caching or timeout change was justified from one successful run, because weakening freshness, citations, source coverage, or context isolation would be worse than the measured wait. The interactive UI immediately showed working/tool status. `START_HERE.md` states the honest one-to-three-minute multi-source expectation.

## User entrypoint

Double-click `Launch Hermes.command`, then follow `START_HERE.md`. The guide covers text, voice, explicit screen selection, Cancel, Mute, Dismiss, healthy startup, normal limitations, and three useful first requests.

## Safety result

No Slack/email was sent, no calendar was changed, no external write was enabled, no logged-in browser or computer control was used, no screenshot was captured during this milestone, and no private acceptance answer or credential was printed or committed. Runtime acceptance artifacts remain ignored and owner-only. The approved Flash/Pro/Luna/Terra router is unchanged; Sol remains builder-only.
