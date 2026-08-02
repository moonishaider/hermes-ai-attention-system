# Current Operational State

**Authoritative as of:** 2 August 2026

**Prompt 4 rollback checkpoint:** `015948b`

**Implemented through:** `731af5f` plus the current acceptance-documentation change

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
| Safety and repository | Live and acceptance-tested | Marked root, hooks/rules, preflight, command negatives, config doctor, secret scan, backup/restore, and 39 tests pass. Private remote is `moonishaider/hermes-ai-attention-system`; Prompt 4 rollback is `015948b`. |
| Daily launch and health | Implemented locally, awaiting voice acceptance | `scripts/launch_daily_hermes.sh` runs preflight, prints credential-safe health, starts the local overlay, launches Hermes with only the trusted project plugin, and tears the overlay down on exit. It creates no server, service, or launch agent. |
| Model routes | Live and representative-task tested | Flash, Pro, Luna, and Terra each passed bounded representative tasks. Flash and Luna tied on deterministic routine quality; Luna was slightly faster in the tiny sample but about 14x more expensive, so Flash remains default. Sol remains builder-only. |
| GitHub personal/company | Live and acceptance-tested for bounded retrieval | Separate `/readonly` connections and 14-tool allowlists remain intact. Personal GitHub participated in two accepted project-resumption runs; company GitHub participated in an accepted source-backed daily-report draft. Write tools remain unavailable. |
| Slack Inside Success/Mitchell | Live with mixed acceptance evidence | Both strict read-only connections participated in an accepted cross-context case with citations and no reported leakage. Inside Success also participated in the accepted report draft. A focused Mitchell live query timed out at 180 seconds; local Codex-only Mitchell open loops passed earlier. |
| Google work/personal | Externally blocked on reauthorization | Prior metadata smokes and exact read-only scopes remain valid evidence, but all six Developer Preview resource access tokens expired and contain no refresh token. They must be reauthorized before current Gmail/Drive/Calendar acceptance; startup health reports the warning. |
| Codex history | Live and acceptance-tested | 187 source files, 64,000 checkpointed lines, bounded ingestion, redaction, tool-output exclusion, and project-resumption retrieval pass. Deterministic calibration reduced unknown from 49.1244% to 47.0728% by reclassifying 198 records from one verified workspace mapping. Genuine ambiguity remains unknown. |
| ChatGPT history | Externally blocked | The official export was requested but no matching ZIP is present. Importer and explicit relay are ready. No continuous ChatGPT account-sync API is claimed. |
| Zoom | Externally blocked on OAuth, not TLS | A normal-TLS retry now reaches the official endpoint and returns HTTP 401, which clears the earlier Cloudflare 526 certificate blocker. Zoom remains disabled until the exact work account and four read scopes are authorized and its post-auth inventory is checked. |
| Attention, handoffs, reports | Partially live and acceptance-tested | Cross-context search, project resumption, and a source-backed daily-report draft passed. Same-day brief/work attribution and personal upcoming obligations did not pass because current evidence or Google authorization was insufficient; the system failed closed instead of inventing facts. |
| Specialists and memory | Implemented and deterministic-tested | Persistent registry loading, context restrictions, namespace-scoped memory proposals, and disabled serious-mode tax/finance behavior pass. Tax/finance remains disabled. |
| Voice and overlay | Implemented locally, awaiting real acceptance | Hermes native streaming voice, local faster-whisper, Edge TTS, free bundled wake word, and the visible overlay are prepared. Microphone permission and real interruption/mute warm-versus-cold acceptance remain. |
| Screen viewing | Implemented locally, awaiting real acceptance | The one-shot adapter consumes one grant, uses the interactive system picker, and stores no screenshot automatically. Screen Recording permission and exactly one Luna acceptance capture remain. |
| Inside Success daily publish | Shadow/preview only | A real evidence-backed draft exists, but no destination is selected, the executor is kill-switched, and no generic send tool is exposed. Nothing has been sent. |
| Safe web/shopping research | Live and acceptance-tested for bounded public research | Pinned `ddgs==9.14.4` search plus guarded public-page fetch return URLs/dates/hashes, flag prompt injection, redact secrets, and block local/credential URLs. A Logitech research smoke returned six cited results and safely fetched one official page. No browser session, cart, checkout, payment, or background browsing exists. |
| Persistent service/launch agent | Intentionally deferred | Daily launch is deliberate and local. No persistent service or launch agent exists. |

## Acceptance result in one sentence

Hermes can currently save time on source-backed project resumption, cross-context evidence gathering, Inside Success report drafting, and public product research, but it cannot yet be called fully accepted for daily briefs, personal obligations, live voice/screen use, Google-backed queries, Zoom, ChatGPT backfill, or Slack publishing.

## Non-negotiable boundaries

No local development server, unrestricted browser/computer control, YOLO mode, generic Slack send, broad filesystem tool, account/admin mutation, company/client write, silent OAuth widening, TLS bypass, payment/checkout, permanent deletion, or launch agent is enabled. Retrieved content is untrusted evidence and must retain source, account, context, date, and confidence labels.
