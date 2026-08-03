# Issues and deferred work

Current evidence levels are authoritative in `implementation/CURRENT_OPERATIONAL_STATE.md`.

## Guarded repository script portability — resolved

The authorized POSIX `tr` normalization fix passed macOS Bash regression tests. The private repository was created and pushed only through guarded scripts.

## Manual gates

- Zoom OAuth, filtered inventory, metadata smoke, and bounded recent-meeting usefulness acceptance are complete without TLS bypass. The provider advertises 12 tools, including two writes that remain filtered out; only four reviewed reads are exposed. Meeting ownership, host sharing, Smart Recording, and Meeting Summary availability can still limit transcript depth.
- Google access tokens remain short-lived without refresh tokens. Work continues through the hosted Workspace MCP; personal consumer access uses standard Google APIs because the Developer Preview provider rejects that account. Reauthorize one resource/account at a time when startup health warns, never by widening scopes.
- The one-shot screen adapter and fixed-destination Slack executor are implemented and covered by synthetic negative/positive tests; neither is exposed for unrestricted runtime use. One selected-region Luna interpretation passed. The macOS toolbar destination-drift screenshot was permanently removed after exact confirmation, and no raw acceptance screenshot remains. The first exact Slack destination/action approval remains a human-only gate.
- The approved official ChatGPT export import is complete: 47 conversations from 1 March onward are indexed as evidence. Current split-shard format, archive bounds, provenance, retrieval, and duplicate rerun pass. All 47 remain `unknown` until semantic calibration; no continuous account sync is claimed.
- Microphone permission, the live microphone-to-spoken-reply loop, automatic TTS, immediate speaker-only barge-in, and the visible overlay controls are complete. The project-local process-only guard prevented interrupted `afplay` from restarting through `ffplay`; the overlay's pinned in-process bridge stopped an active API call without another model turn. Local Whisper can still mishear short utterances (observed “great” as “grade”), and the cancel seam must be revalidated before any Hermes upgrade.
- One-shot screen interpretation, exact screenshot privacy cleanup, and visible overlay controls are accepted. Bounded real-data calibration is complete, with documented misses and latency limitations.

No local dev server, live message/calendar/form action, or macOS permission request was performed. Authorized browser control was limited to account-scoped connector setup; no broad browser/computer control was enabled.
