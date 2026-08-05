# Issues and deferred work

Current evidence levels are authoritative in `implementation/CURRENT_OPERATIONAL_STATE.md`.

## Prompt 6 visible acceptance — resolved

The official Desktop migration passed owner-visible Stop speaking, wake-off silence, native Attention selected-area interpretation with no retained screenshot, explicit preference learning, plain learning status, close/reopen Quick Entry, full quit with no residual processes, and clean relaunch. The radial Memory Graph remains an advanced view because it was not self-explanatory; Attention now provides the ordinary plain-language learning summary.

The official Desktop SDK does not expose a clean supported second global shortcut that starts voice capture. Quick Entry remains Command+Shift+Space; voice uses the obvious microphone or optional local Hey Jarvis. Control+Shift+S stops current speech. No unsupported desktop automation was added.

The project-specific Desktop build is locally ad-hoc signed and passes strict signature verification, but is not Apple-notarized. The official downloaded bootstrap was notarized. The bundle reports 0.17.0 while its installed Hermes Agent runtime reports 0.20.0 (2026.8.3); this upstream version-label mismatch is documented rather than hidden.

Hermes uses SQLite 3.42.0, so 0.20.0 deliberately falls back to `journal_mode=DELETE` rather than unsafe WAL. Doctor otherwise passes. This is an upstream runtime limitation, not a data-integrity failure; final backups pass SQLite quick checks.

## Guarded repository script portability — resolved

The authorized POSIX `tr` normalization fix passed macOS Bash regression tests. The private repository was created and pushed only through guarded scripts.

## Manual gates

- Zoom OAuth, filtered inventory, metadata smoke, and bounded recent-meeting usefulness acceptance are complete without TLS bypass. The provider advertises 12 tools, including two writes that remain filtered out; only four reviewed reads are exposed. Meeting ownership, host sharing, Smart Recording, and Meeting Summary availability can still limit transcript depth.
- Google hourly reauthorization is resolved. Work and personal each have one exact-scope offline grant; forced refresh and all six standard-API metadata smokes pass. The launcher and direct clients refresh automatically. Google can still revoke a refresh token after account-security events, credential rotation, organization session policy, prolonged non-use, or user revocation. Personal verification remains intentionally deferred because this is a private single-user app; the unverified warning is expected.
- The one-shot screen adapter and destination-locked Slack executor are implemented and covered by synthetic negative/positive tests; neither is exposed for unrestricted runtime use. The Slack lock targets only workspace `T01K1TNLXLK` / `#sd-dloa-tyler` (`C0B0RT26KCZ`). The current v2 private preview contains four confirmed claims with validated company Slack permalinks and expired safely. A fresh exact payload and explicit approval remain required if a supervised send is ever requested; no message has been sent.
- Syed requested the personal Gemini Google Takeout export. Delivery is pending. The importer remains deferred until the official ZIP can be previewed for schema/count/size/date range; no guessed format or continuous synchronization is claimed.
- The approved official ChatGPT export import is complete: 47 conversations from 1 March onward are indexed as evidence. Current split-shard format, archive bounds, provenance, retrieval, and duplicate rerun pass. All 47 remain `unknown` until semantic calibration; no continuous account sync is claimed.
- Microphone permission, native microphone-to-spoken-reply, local wake detection, shorter natural voice projection, and immediate post-rebuild Stop speaking all pass. Typed automatic TTS is deliberately off. Spoken barge-in remains available during active voice conversation, with the permanent Attention button and Control+Shift+S as discoverable fallbacks. Local Whisper can still mishear short utterances (observed “great” as “grade”).
- One-shot screen interpretation, exact screenshot privacy cleanup, and visible overlay controls are accepted. Deterministic provenance calibration is complete; a 12-item owner-only semantic calibration packet is ready but unapplied. Slow multi-connector queries remain a quality limitation, mitigated by strict-valid local composition rather than repeated live calls.

No local development server, live message/calendar/form action, custom daemon, launch agent, or broad browser/computer control was enabled. Prompt 6 used only the already-approved native microphone/Desktop Folder permissions and preserved every external-action boundary.
