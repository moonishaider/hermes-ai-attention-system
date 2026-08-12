# Prompt 7 Talk and Model-Governor Correction — 12 August 2026

## Owner-reported defect

The visible Jarvis **Talk** control appeared unclickable. The packaged renderer previously allowed a rejected WebKit microphone request or unavailable `MediaRecorder` path to fail without any visible explanation. It also did not cancel an already-running answer before trying to listen.

## Correction installed

- Talk remains permanently visible in the main header and Quick Entry HUD.
- A click now stops spoken output, cancels an in-progress model run, opens Chat, and starts one explicit microphone recording.
- Success changes the control to **Stop listening** and shows `Listening until you press Stop…`.
- A missing WebKit media API, rejected permission, or capture error now produces a visible `Talk could not start` explanation and explicitly confirms that nothing was recorded or submitted.
- Audio remains in memory only for the bounded transcription/retry path. This change adds no wake listener, continuous microphone, file retention, browser control, or external write.

The owner-visible click result passed in the installed application. Automated renderer coverage also proves both reachability and fail-visible behavior.

The first owner click on the corrected package exposed `NotAllowedError`, proving the button handler was active while the packaged WKWebView had no usable native microphone consent. A second package then exposed the native AVFoundation state as `Denied`, while Jarvis was absent from the visible Microphone list. The final correction now:

- asks AVFoundation for the exact app's native microphone authorization before invoking `getUserMedia`;
- waits visibly for the macOS decision and distinguishes authorized, denied, restricted, and incomplete states;
- signs the bundle with the single Apple audio-input entitlement `com.apple.security.device.audio-input`;
- retains `NSMicrophoneUsageDescription` in the installed Info.plist;
- clears only the stale `com.moonishaider.jarvis` Microphone decision after installation; and
- logs owned-gateway startup diagnostics to an owner-only runtime file outside Git instead of discarding failures.

Apple's current media-capture documentation requires explicit owner authorization and identifies the audio-input entitlement for microphone capture. No camera, Accessibility, screen-control, filesystem, browser, or external-write entitlement was added. Syed completed that exact gate and visibly confirmed Talk, record, and Stop worked.

The first captured request was substantially mistranscribed by the local Whisper `base` model. A bounded comparison used three existing synthetic Ryan voice fixtures only. On the fixture designed to say “Hermes Voice Synthetic Test,” local STT returned “Kurmi's voice synthetic test” in 2.28 s while `gpt-4o-mini-transcribe` returned the exact phrase in 2.40 s. On two warm fixtures the cloud route also corrected Hermes proper-name errors and completed in 2.06 s versus 2.22 s and 1.54 s versus 1.82 s. Syed's next real dictated sentence was nevertheless still materially wrong, so quality acceptance failed and Jarvis moved to the higher-accuracy official `gpt-4o-transcribe` route with its supported English-language and bounded domain-vocabulary hints. A second three-fixture pass returned the exact expected text for all three files in 2.30–2.98 seconds. Jarvis retains local STT as a fail-safe fallback and supports the explicit `JARVIS_STT_PROVIDER=local` privacy override. Long recording uses 500 ms memory-only chunks. If the live WebKit transcript and final transcription materially disagree, Jarvis now stages the final text in the composer, retains the in-memory recording, and submits nothing until the owner reviews, retries, or discards it. Otherwise audio remains available only until Hermes confirms a run receipt; failure exposes Retry transcription, Edit transcript, and Discard, while successful receipt releases the raw recording. No transcript fixture contains private source content. One real owner sentence remains necessary to measure the final room-accuracy result honestly.

The gateway diagnostic also exposed a reproducible macOS/aiohttp fixed-port conflict during immediate quit/reopen. Jarvis now creates a private process group for the exact gateway it owns, terminates that group gracefully, serializes startup, and asks macOS for a fresh private loopback port on every launch. The selected port and bearer credential remain native-only and never reach React or logs. A new launch therefore cannot attach to or collide with the prior listener while macOS completes teardown. No development server is involved.

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

- 90 Python unit/security/contract tests passed.
- 4 renderer tests passed.
- 6 Rust policy/lifecycle tests passed in the current fixed-navigation build.
- TypeScript/Vite production build, Rust formatting, Clippy with warnings denied, release application build, ad-hoc code-signature verification, secret scan, configuration doctor, safety preflight, command-rule negatives, and production npm audit passed.
- Production npm audit reported zero vulnerabilities.
- Current installed binary SHA-256: `f61b90d240ced22184cb9920251de762781fe879d7148826ac6f79a6e1498b26` (the later production-only build adds fixed-destination navigation, transcript-disagreement review, and recoverable Capability Studio feedback; the governor implementation remains unchanged).
- The installed app owns one Hermes gateway on a fresh authenticated loopback-only port selected by macOS per launch; no development server is involved.
- Normal application Quit terminated the exact gateway process group, and two clean reopens each received a different healthy loopback port with one app and one owned gateway.
- The immediately preceding app is preserved at `backups/Jarvis-pre-talk-fix-20260812T000151Z.app`.
- Additional pre-permission-bridge rollback bundles are preserved at `backups/Jarvis-pre-native-microphone-20260812T0527.app`, `backups/Jarvis-native-microphone-pre-gateway-log-20260812T0538.app`, and `backups/Jarvis-pre-audio-entitlement-20260812T0540.app`.
- The immediately preceding fixed-port application is preserved at `backups/Jarvis-pre-dynamic-loopback-20260812T012901Z.app`.

No Slack/email was sent, no calendar was changed, and no company/client write or unrestricted control was enabled.
