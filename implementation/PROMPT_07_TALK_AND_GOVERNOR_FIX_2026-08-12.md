# Prompt 7 Talk and Model-Governor Correction — 12 August 2026

## Owner-reported defect

The visible Jarvis **Talk** control appeared unclickable. The packaged renderer previously allowed a rejected WebKit microphone request or unavailable `MediaRecorder` path to fail without any visible explanation. It also did not cancel an already-running answer before trying to listen.

## Correction installed

- Talk remains permanently visible in the main header and Quick Entry HUD.
- A click now stops spoken output, cancels an in-progress model run, opens Chat, and starts one explicit microphone recording.
- Success changes the control to **Stop listening** and shows `Listening until you press Stop…`.
- A missing WebKit media API, rejected permission, or capture error now produces a visible `Talk could not start` explanation and explicitly confirms that nothing was recorded or submitted.
- Audio remains in memory only for the bounded transcription/retry path. This change adds no wake listener, continuous microphone, file retention, browser control, or external write.

The owner-visible click result is still required before the Talk item is marked passed. Automated renderer coverage proves both reachability and fail-visible behavior.

The first owner click on the corrected package exposed `NotAllowedError`, proving the button handler was active while macOS still held a denied microphone decision for `com.moonishaider.jarvis`. Only that bundle's Microphone decision was reset with `tccutil`; no other application or permission was touched. The final Allow decision remains a macOS human gate.

## Model-governor correction

The same reviewed package closes a separate Prompt 7 policy gap:

- routine work starts on DeepSeek V4 Flash;
- difficult or attribution-sensitive work uses DeepSeek V4 Pro;
- high-stakes work now performs Pro synthesis followed by an independent GPT-5.6 Terra review, rather than routing directly to Terra;
- an empty or token-limit-truncated Flash result escalates to Pro;
- Auto, Flash, Pro, and Pro + Terra are visible bounded owner overrides;
- GPT-5.6 Sol remains structurally unavailable to Jarvis;
- the UI clears the preliminary draft when the governed second stage starts, shows the escalation/review reason, preserves cancellation against the active stage, and totals stage cost and tokens.

The previously accepted direct Terra connectivity result remains valid provider evidence. The new two-stage path is implemented and tested, but will not be described as owner-visible acceptance until a packaged run exercises it.

## Verification and installation

- 86 Python unit/security/contract tests passed.
- 2 renderer tests passed.
- 4 Rust policy/lifecycle tests passed.
- TypeScript/Vite production build, Rust formatting, Clippy with warnings denied, release application build, ad-hoc code-signature verification, secret scan, configuration doctor, safety preflight, command-rule negatives, and production npm audit passed.
- Production npm audit reported zero vulnerabilities.
- Installed binary SHA-256: `f09cc66432d116154114e2e6b76c0352d54d1def8b4404d238412bad9e26b0c3`.
- The installed app owns one Hermes gateway on authenticated loopback `127.0.0.1:8642`; no development server is involved.
- The immediately preceding app is preserved at `backups/Jarvis-pre-talk-fix-20260812T000151Z.app`.

No Slack/email was sent, no calendar was changed, and no company/client write or unrestricted control was enabled.
