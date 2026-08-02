# Current Operational State

**Authoritative as of:** 2 August 2026  
**Repository checkpoint:** `015948b`  
**Purpose:** This is the single current source of truth. Historical milestone records remain useful evidence but may describe earlier states.

## Evidence levels

- **Live and acceptance-tested:** exercised against bounded real data with source/context and leakage checks.
- **Live but metadata-smoked:** authenticated and read-only inventory/metadata probes passed; usefulness on real content is not yet accepted.
- **Implemented locally, awaiting real acceptance:** code and synthetic/contract tests pass, but a supervised real-world test is outstanding.
- **Shadow/preview only:** deliberately cannot perform the external action in normal Hermes runtime.
- **Externally blocked:** prepared correctly but blocked by a provider or required human artifact.
- **Intentionally deferred:** excluded from this milestone for safety, scope, or lack of demonstrated need.

## Current status

| Area | Evidence level | Current truth |
|---|---|---|
| Safety and repository | Live and acceptance-tested | Marked root, project hooks/rules, safety preflight, command-policy negatives, guarded private push, backup/restore, config doctor, secret scan, and 30 tests pass. Private remote is `moonishaider/hermes-ai-attention-system`. |
| Hermes runtime | Live but metadata-smoked | Official Hermes `0.19.1 (2026.7.30)` is installed. The guarded launcher enables only the reviewed project plugin. Project status was called first and external writes remain disabled. Daily-use acceptance is pending. |
| Model routes | Live but synthetic-quality-smoked | DeepSeek V4 Flash/Pro and GPT-5.6 Luna/Terra direct routes pass small synthetic calls. Representative quality, citation, tool-use, latency, and cost evaluation remains pending. Sol is builder-only. |
| GitHub personal/company | Live but metadata-smoked | Two separate `/readonly` connections, 14 tools each, owner boundaries, private visibility, and negative write-tool tests pass. Bounded real retrieval acceptance is pending. |
| Slack Inside Success/Mitchell | Live but metadata-smoked | Separate apps/tokens/browser boundaries; exactly 14 read scopes and seven read/search tools each. Agent-app experiences and send tools are off. Bounded real retrieval acceptance is pending. |
| Google work/personal | Live but metadata-smoked | Separate Gmail, Drive, and Calendar resource tokens and read allowlists are active. Metadata probes pass. Real retrieval acceptance and token-expiry health reporting remain pending. |
| Codex history | Live and acceptance-tested for ingestion | Incremental, bounded ingestion with checkpoints, cutoff, secret redaction, tool-output exclusion, and resource measurements passes. Context quality has a large unknown baseline and requires Prompt 4 calibration. |
| ChatGPT history | Externally blocked | Official export importer and explicit relay are implemented. Syed requested the export; the ZIP has not arrived or been selected. No continuous account-sync API is claimed. |
| Zoom | Externally blocked | Work identity/license and the exact four read scopes/tools are prepared. Zoom Marketplace returned provider-side TLS/Cloudflare 526; Zoom remains disabled. |
| Attention, handoffs, reports, specialists, memory | Implemented locally, awaiting real acceptance | Local engines and synthetic tests pass. Prompt 4 must prove bounded real-data usefulness, source labeling, serious-mode restrictions, and cross-context isolation. |
| Voice and overlay | Implemented locally, awaiting real acceptance | Dependencies and synthetic TTS-to-STT pass; overlay controls exist. Microphone permission and real interruption/mute/latency acceptance are pending. |
| Screen viewing | Implemented locally, awaiting real acceptance | One-shot interactive adapter consumes a single grant and retains no file automatically. Screen Recording permission and exactly one Luna acceptance capture are pending. |
| Inside Success daily publish | Shadow/preview only | Destination-locked executor, hash/TTL/idempotency/audit/kill-switch tests pass synthetically. No destination is selected, no real sender is exposed, and nothing has been sent. |
| Safe web/shopping research | Intentionally deferred until Prompt 4 implementation | No logged-in browser, cart, checkout, payment, or background browsing is enabled. A read-only cited search/fetch path remains to be implemented and accepted. |
| Persistent service/launch agent | Intentionally deferred | Daily launch remains deliberate and local. No persistent service or launch agent will be created without a separate decision. |

## Prompt 4 acceptance gates

1. Run bounded real-data retrieval and context-leakage acceptance across the six live logical connector groups plus Codex.
2. Measure and improve deterministic Codex classification without forcing ambiguous evidence.
3. Run representative model-quality evaluation; retain routing unless evidence supports a reviewed change.
4. Complete one-at-a-time Microphone and Screen Recording gates.
5. Preview/import the official ChatGPT export only after the ZIP arrives and Syed identifies it.
6. Retry Zoom once through normal TLS; keep disabled on failure.
7. Ask Syed to select the exact Inside Success Slack destination before preparing any live-action approval.
8. Add a read-only, cited, prompt-injection-aware web research path.

## Non-negotiable boundaries

No local development server, unrestricted browser/computer control, YOLO mode, generic Slack send, broad filesystem tool, account/admin mutation, company/client write, silent OAuth widening, TLS bypass, payment/checkout, permanent deletion, or launch agent is enabled. Runtime source content is untrusted evidence and must retain source, account, context, date, and confidence labels.
