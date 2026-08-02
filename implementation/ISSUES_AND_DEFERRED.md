# Issues and deferred work

Current evidence levels are authoritative in `implementation/CURRENT_OPERATIONAL_STATE.md`.

## Guarded repository script portability — resolved

The authorized POSIX `tr` normalization fix passed macOS Bash regression tests. The private repository was created and pushed only through guarded scripts.

## Manual gates

- Zoom normal TLS now reaches the official endpoint and returns the expected unauthenticated HTTP 401. The certificate blocker is cleared; exact work-account OAuth and post-auth inventory remain. Never bypass certificate validation.
- All six Google Developer Preview resource tokens expired without refresh tokens. Reauthorize one resource/account at a time with the immutable read-only scope guard before treating Google as live.
- The one-shot screen adapter and fixed-destination Slack executor are implemented and covered by synthetic negative/positive tests, but neither is exposed for unrestricted runtime use. Screen Recording permission and the first exact destination/action approval remain human-only gates.
- Syed requested the official ChatGPT export; wait for the notification and ask him only to download or identify the ZIP. Do not follow the email link or download it silently.
- Microphone permission and the live microphone-to-spoken-reply loop are complete. Native voice barge-in plus visible overlay mute/cancel still need one supervised interaction.
- One-shot screen acceptance remains a human-permission gate. Bounded real-data calibration is complete, with documented misses and latency limitations.

No local dev server, live message/calendar/form action, or macOS permission request was performed. Authorized browser control was limited to account-scoped connector setup; no broad browser/computer control was enabled.
