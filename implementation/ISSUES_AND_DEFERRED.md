# Issues and deferred work

Current evidence levels are authoritative in `implementation/CURRENT_OPERATIONAL_STATE.md`.

## Guarded repository script portability — resolved

The authorized POSIX `tr` normalization fix passed macOS Bash regression tests. The private repository was created and pushed only through guarded scripts.

## Manual gates

- Zoom work identity, licensing, endpoint, scopes, and four-tool allowlist are verified. App creation is temporarily blocked by a Zoom Marketplace Cloudflare 526 host-certificate error observed on 2026-08-02; retry only through normal TLS and never bypass certificate validation. Work/personal Google, GitHub, and both Slack connections are live.
- The one-shot screen adapter and fixed-destination Slack executor are implemented and covered by synthetic negative/positive tests, but neither is exposed for unrestricted runtime use. Screen Recording permission and the first exact destination/action approval remain human-only gates.
- Syed requested the official ChatGPT export; wait for the notification and ask him only to download or identify the ZIP. Do not follow the email link or download it silently.
- Decide whether to grant narrow macOS Microphone and Screen Recording permissions; adapters are ready.
- Run real-data context/attention calibration and native live-microphone acceptance. The backup/restore drill passed.

No local dev server, live message/calendar/form action, or macOS permission request was performed. Authorized browser control was limited to account-scoped connector setup; no broad browser/computer control was enabled.
