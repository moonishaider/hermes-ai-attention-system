# Current Operational State

**Authoritative as of:** 2 August 2026

**Prompt 4 rollback checkpoint:** `015948b`

**Implemented through:** `b87012c` plus the current voice-acceptance documentation change

**Purpose:** This is the single current source of truth. Historical milestone records are evidence of what was true when written, not the present status.

## Evidence levels

- **Live and acceptance-tested:** exercised against bounded real data with source/context and leakage checks.
- **Live but metadata-smoked:** authenticated inventory or metadata probes passed; real usefulness is not yet accepted.
- **Implemented locally, awaiting real acceptance:** code and deterministic tests pass; a supervised real test remains.
- **Shadow/preview only:** deliberately unable to perform the external action in normal Hermes runtime.
- **Externally blocked:** prepared but waiting on a provider, credential, permission, or official artifact.
- **Intentionally deferred:** excluded for safety or lack of demonstrated need.

## Current status

| Area | Evidence level | Current truth |
|---|---|---|
| Safety and repository | Live and acceptance-tested | Marked root, hooks/rules, preflight, command negatives, config doctor, secret scan, backup/restore, and 40 tests pass. Private remote is `moonishaider/hermes-ai-attention-system`; Prompt 4 rollback is `015948b`. |
| Daily launch and health | Implemented locally; voice path accepted | `scripts/launch_daily_hermes.sh` runs preflight, prints credential-safe health, starts the local overlay, launches Hermes with only the trusted project plugin, and tears the overlay down on exit. It creates no server, service, or launch agent. The native microphone-to-spoken-reply path is accepted; the complete launcher's visual/control path still needs one supervised daily-use pass. |
| Model routes | Live and representative-task tested | Flash, Pro, Luna, and Terra each passed bounded representative tasks. Flash and Luna tied on deterministic routine quality; Luna was slightly faster in the tiny sample but about 14x more expensive, so Flash remains default. Sol remains builder-only. |
| GitHub personal/company | Live and acceptance-tested for bounded retrieval | Separate `/readonly` connections and 14-tool allowlists remain intact. Personal GitHub participated in two accepted project-resumption runs; company GitHub participated in an accepted source-backed daily-report draft. Write tools remain unavailable. |
| Slack Inside Success/Mitchell | Live with mixed acceptance evidence | Both strict read-only connections participated in an accepted cross-context case with citations and no reported leakage. Inside Success also participated in the accepted report draft. A focused Mitchell live query timed out at 180 seconds; local Codex-only Mitchell open loops passed earlier. |
| Google work/personal | Externally blocked on reauthorization | Prior metadata smokes and exact read-only scopes remain valid evidence, but all six Developer Preview resource access tokens expired and contain no refresh token. They must be reauthorized before current Gmail/Drive/Calendar acceptance; startup health reports the warning. |
| Codex history | Live and acceptance-tested | 187 source files, 64,000 checkpointed lines, bounded ingestion, redaction, tool-output exclusion, and project-resumption retrieval pass. Deterministic calibration reduced unknown from 49.1244% to 47.0728% by reclassifying 198 records from one verified workspace mapping. Genuine ambiguity remains unknown. |
| ChatGPT history | Externally blocked | The official export was requested but no matching ZIP is present. Importer and explicit relay are ready. No continuous ChatGPT account-sync API is claimed. |
| Zoom | Externally blocked on OAuth, not TLS | A normal-TLS retry now reaches the official endpoint and returns HTTP 401, which clears the earlier Cloudflare 526 certificate blocker. Zoom remains disabled until the exact work account and four read scopes are authorized and its post-auth inventory is checked. |
| Attention, handoffs, reports | Partially live and acceptance-tested | Cross-context search, project resumption, and a source-backed daily-report draft passed. Same-day brief/work attribution and personal upcoming obligations did not pass because current evidence or Google authorization was insufficient; the system failed closed instead of inventing facts. |
| Specialists and memory | Implemented and deterministic-tested | Persistent registry loading, context restrictions, namespace-scoped memory proposals, and disabled serious-mode tax/finance behavior pass. Tax/finance remains disabled. |
| Voice and overlay | Native voice and speaker-only barge-in accepted; visible controls pending | A deliberate microphone phrase passed local faster-whisper transcription, DeepSeek Flash response, and audible Edge TTS. Syed selected the British male `en-GB-RyanNeural` voice. Enabling the previously false `voice.auto_tts` fixed silent ordinary replies. On the corrected no-headphones retest, Syed said “stop,” Ryan stopped immediately, Hermes transcribed the correction, and it answered without replaying the interrupted audio. Continuous mode then correctly remained listening; local Whisper misheard a later “great” as “grade,” producing a confusing but separate response. Visible overlay mute/cancel remain. |
| Screen viewing | Luna route accepted; final Trash cleanup pending | On 2026-08-03 Syed selected one Codex region through Apple's visible screenshot UI and GPT-5.6 Luna returned a bounded description successfully in 4.95 seconds for an estimated $0.0051. No continuous capture, Accessibility permission, or computer control was enabled. macOS 26 ignored the requested destination when its full toolbar was used, so the exact Desktop screenshot was moved uninspected to Git-ignored owner-only quarantine, processed once, then moved recoverably to Trash. The permanent adapter now uses selection-only mode with a private temporary file that is removed before return. Permanent deletion of the one recoverable Trash copy remains an explicit confirmation gate. |
| Inside Success daily publish | Shadow/preview only | A real evidence-backed draft exists, but no destination is selected, the executor is kill-switched, and no generic send tool is exposed. Nothing has been sent. |
| Safe web/shopping research | Live and acceptance-tested for bounded public research | Pinned `ddgs==9.14.4` search plus guarded public-page fetch return URLs/dates/hashes, flag prompt injection, redact secrets, and block local/credential URLs. A Logitech research smoke returned six cited results and safely fetched one official page. No browser session, cart, checkout, payment, or background browsing exists. |
| Persistent service/launch agent | Intentionally deferred | Daily launch is deliberate and local. No persistent service or launch agent exists. |

## Acceptance result in one sentence

Hermes can currently save time on source-backed project resumption, cross-context evidence gathering, Inside Success report drafting, public product research, and live spoken interaction, but it cannot yet be called fully accepted for daily briefs, personal obligations, screen use, Google-backed queries, Zoom, ChatGPT backfill, or Slack publishing.

## Non-negotiable boundaries

No local development server, unrestricted browser/computer control, YOLO mode, generic Slack send, broad filesystem tool, account/admin mutation, company/client write, silent OAuth widening, TLS bypass, payment/checkout, permanent deletion, or launch agent is enabled. Retrieved content is untrusted evidence and must retain source, account, context, date, and confidence labels.
