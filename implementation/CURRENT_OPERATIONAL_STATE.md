# Current Operational State

**Authoritative as of:** 4 August 2026

**Prompt 4 rollback checkpoint:** `015948b`

**Implemented through:** `c05d816` plus the current Zoom activation and acceptance changes

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
| Safety and repository | Live and acceptance-tested | Marked root, hooks/rules, preflight, command negatives, config doctor, secret scan, backup/restore, and 48 tests pass. Private remote is `moonishaider/hermes-ai-attention-system`; Prompt 4 rollback is `015948b`, and the pre-overlay rollback is `f956ef3`. |
| Daily launch and health | Live and acceptance-tested | `scripts/launch_daily_hermes.sh` runs preflight, prints credential-safe health, starts the local overlay, launches Hermes with only the trusted project plugin, and tears the overlay down on exit. It creates no server, service, or launch agent. The native microphone-to-spoken-reply path and the complete launcher's visual/control path are accepted. |
| Model routes | Live and representative-task tested | Flash, Pro, Luna, and Terra each passed bounded representative tasks. Flash and Luna tied on deterministic routine quality; Luna was slightly faster in the tiny sample but about 14x more expensive, so Flash remains default. Sol remains builder-only. |
| GitHub personal/company | Live and acceptance-tested for bounded retrieval | Separate `/readonly` connections and 14-tool allowlists remain intact. Personal GitHub participated in two accepted project-resumption runs; company GitHub participated in an accepted source-backed daily-report draft. Write tools remain unavailable. |
| Slack Inside Success/Mitchell | Live with mixed acceptance evidence | Both strict read-only connections participated in an accepted cross-context case with citations and no reported leakage. Inside Success also participated in the accepted report draft. A focused Mitchell live query timed out at 180 seconds; local Codex-only Mitchell open loops passed earlier. |
| Google work | Live and acceptance-tested | Gmail, Drive, and Calendar were separately reauthorized on 3 August with the unchanged exact read-only scopes. Each metadata-only probe passed. A bounded Inside Success brief then used Gmail and Calendar alongside Codex, GitHub, and Slack: 9/9 claims cited, 8 confirmed and 1 inferred, no reported leakage. A same-day work-attribution case also passed with 6/6 claims cited, 5 confirmed and 1 uncertain, and no reported leakage or other-person attribution. Raw provider write tools remain excluded. |
| Google personal | Live and acceptance-tested through direct read-only APIs | Profile 1 reauthorization granted exactly the reviewed Gmail, Drive, and Calendar read scopes to `moonishaider12@gmail.com`; token files are owner-only and short-lived. The hosted Workspace MCP preview rejects consumer accounts, so its three personal endpoints are disabled. Three host-locked GET-only project tools use the standard Google APIs instead. Metadata smokes passed, and a 1–10 August personal-obligations case passed with 6/6 cited claims, 5 confirmed and 1 inferred, mixed evidence retained as mixed, no reported leakage, 68.4 s latency, and $0.00308 estimated model cost. |
| Codex history | Live and acceptance-tested | 187 source files, 64,000 checkpointed lines, bounded ingestion, redaction, tool-output exclusion, and project-resumption retrieval pass. Deterministic calibration reduced unknown from 49.1244% to 47.0728% by reclassifying 198 records from one verified workspace mapping. Genuine ambiguity remains unknown. |
| ChatGPT history | Live and acceptance-tested for official backfill | The user-selected 308.8 MB official ZIP contained five contiguous `conversations-NNN.json` shards. Preview selected 47 of 458 conversations from 1 March onward at about 120 MiB maximum RSS. Exact approval imported 47 records; a rerun reported 47 duplicates, all 47 provenance records validated, and source-backed retrieval passed without printing content. The records remain evidence, with 46 inferred and 1 uncertain; all remain `unknown` pending semantic calibration. No continuous account-sync API is claimed. |
| Zoom | Live and acceptance-tested for bounded retrieval | `Hermes Work Zoom Read Only` is a user-managed Profile 2 app using secretless public-client PKCE. The grant contains exactly the four reviewed meeting/recording read scopes, shared-access widening stayed unchecked, and owner-only refreshable token state is active. Live discovery returned 12 provider tools; Hermes exposes only four reviewed reads and excludes the two observed Canvas/Hub writes. A bounded 1–4 August case retrieved three recent work-meeting evidence references: 3/3 claims cited and confirmed, no reported leakage, 65.5 s latency, and $0.00523 estimated model cost. |
| Attention, handoffs, reports | Partially live and acceptance-tested | Cross-context search, project resumption, a source-backed daily-report draft, the work daily brief, same-day work attribution, recent Zoom meeting retrieval, and personal upcoming obligations pass. Slack publishing remains shadow-only. |
| Specialists and memory | Implemented and deterministic-tested | Persistent registry loading, context restrictions, namespace-scoped memory proposals, and disabled serious-mode tax/finance behavior pass. Tax/finance remains disabled. |
| Voice and overlay | Live and acceptance-tested | A deliberate microphone phrase passed local faster-whisper transcription, DeepSeek Flash response, and audible Edge TTS. Syed selected the British male `en-GB-RyanNeural` voice. On the corrected no-headphones retest, spoken barge-in stopped Ryan immediately without replay. On 2026-08-03 the foreground launcher showed the visible transcript/status/context surface; Mute/Unmute changed only its owner-only ephemeral voice-output state, Cancel stopped an active Flash API call after about seven seconds without a follow-up turn, Dismiss hid the window, and Approve remained disabled without an exact preview hash. The bridge is project-local and pinned to Hermes 0.19.1's native `agent.interrupt()` seam. Local Whisper can still mishear very short utterances. |
| Screen viewing | Live and acceptance-tested | On 2026-08-03 Syed selected one Codex region through Apple's visible screenshot UI and GPT-5.6 Luna returned a bounded description successfully in 4.95 seconds for an estimated $0.0051. No continuous capture, Accessibility permission, or computer control was enabled. macOS 26 ignored the requested destination when its full toolbar was used, so the exact Desktop screenshot was moved uninspected to Git-ignored owner-only quarantine, processed once, then moved recoverably to Trash. After Syed explicitly confirmed deletion of that exact file, it was permanently removed; Finder verified that the other six Trash items remained. No raw acceptance screenshot remains. The permanent adapter uses selection-only mode with a private temporary file that is removed before return. |
| Inside Success daily publish | Shadow/preview only | A real evidence-backed draft exists, but no destination is selected, the executor is kill-switched, and no generic send tool is exposed. Nothing has been sent. |
| Safe web/shopping research | Live and acceptance-tested for bounded public research | Pinned `ddgs==9.14.4` search plus guarded public-page fetch return URLs/dates/hashes, flag prompt injection, redact secrets, and block local/credential URLs. A Logitech research smoke returned six cited results and safely fetched one official page. No browser session, cart, checkout, payment, or background browsing exists. |
| Persistent service/launch agent | Intentionally deferred | Daily launch is deliberate and local. No persistent service or launch agent exists. |

## Acceptance result in one sentence

Hermes can currently save time on source-backed project resumption, cross-context evidence gathering, Inside Success briefing and work attribution, recent Zoom-meeting retrieval, personal obligations, official ChatGPT backfill retrieval, report drafting, public product research, live spoken interaction, visible overlay control, and explicit one-shot screen interpretation. Slack publishing remains incomplete.

## Non-negotiable boundaries

No local development server, unrestricted browser/computer control, YOLO mode, generic Slack send, broad filesystem tool, account/admin mutation, company/client write, silent OAuth widening, TLS bypass, payment/checkout, permanent deletion, or launch agent is enabled. Retrieved content is untrusted evidence and must retain source, account, context, date, and confidence labels.
