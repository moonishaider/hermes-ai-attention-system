# Operational test evidence

Checked: 4 August 2026

| Check | Result |
|---|---|
| Safety preflight, persisted hook tests, command-rule tests | Passed |
| Python unit, integration, security, history, action, model-route, health, specialist, voice-compatibility, web, Google direct-read, and Zoom OAuth tests | 55 passed |
| Configuration doctor and JSON/TOML validation | Passed |
| Versionable-file secret scan | Passed |
| Git diff whitespace check | Passed |
| Hermes version | `0.19.1 (2026.7.30)`, commit `cc4cab2f...` |
| Hermes broad-tool negative inventory | Broad tools disabled; `hermes_attention` enabled |
| Voice dependency imports | Passed |
| Synthetic Edge TTS to local faster-whisper | Passed; 16,272 bytes; transcript not printed; 16.45 s; peak 399.8 MB |
| Real Codex bounded ingestion | Additional 50×1,000-record pass completed; 9,525 total conversation items; 4,784 Inside Success/4,741 unknown; tool output/reasoning excluded |
| Recorded larger Codex pass resources | 50,000 scanned in 74.1 s; peak 435.4 MB; no content printed |
| SQLite backup to new file | Integrity `ok`; 1,842 evidence rows |
| Screen adapter | Grant and single-use semantics passed; OS permission not requested |
| Supervised action | Kill switch, destination, approval/hash, and negative destination tests passed with synthetic sender |
| DeepSeek V4 Flash live smoke | Passed; 1,265 ms; 100 input/16 output tokens; estimated `$0.00001848` |
| DeepSeek V4 Pro live smoke | Passed; 1,670 ms; 21 input/24 output tokens; estimated `$0.000030015` |
| Hermes one-shot master assistant | Passed; called project status first and reported `external writes enabled: false` |
| GPT-5.6 Luna live vision smoke | Passed with synthetic 1-pixel image; 3,478 ms; 24 input/20 output tokens; estimated `$0.000144` |
| GPT-5.6 Terra live review smoke | Passed; 2,310 ms; 22 input/9 output tokens; estimated `$0.00019` |
| Connector inventories | GitHub personal/company, both Slack workspaces, work Gmail/Drive/Calendar, personal Gmail/Drive/Calendar direct reads, and Zoom are live. Unsupported personal Workspace MCP endpoints are disabled. Zoom granted exactly four read scopes; 12 raw tools were discovered while only four reads are exposed. |
| Resumable onboarding | The 2026-08-02 schema-v2 pass completed project/Hermes/plugin/voice dependencies, bounded Codex ingestion, and all four model smokes. Subsequent Prompt 4 work completed Zoom, microphone, screen, personal Google, and the selected ChatGPT import; the exact Slack destination remains. |
| ChatGPT official export | Current five-shard official format validated; 458 total, 47 selected since 1 March, 47 imported, 47/47 duplicate rerun, all provenance valid, retrieval passed, source content not printed; about 120 MiB preview maximum RSS |
| GitHub personal MCP | Live through `/mcp/readonly`; authenticated `moonishaider`; private project metadata read; 14 exact read tools allowed |
| GitHub personal negative write | `create_or_update_file` resolved to `BLOCKED_TOOL_UNAVAILABLE`; no network write attempted |
| GitHub Inside Success MCP | Live through separate `/mcp/readonly`; 36 authorized repositories visible; metadata-only smoke passed; no approval pending |
| GitHub Inside Success negative write | `create_or_update_file` resolved to `BLOCKED_TOOL_UNAVAILABLE`; no Inside Success write attempted |
| Inside Success Slack strict OAuth | Accidental broad grant revoked and quarantined; corrected flow granted exactly 14 reviewed read scopes with no extras |
| Inside Success Slack MCP inventory | Connected in 3,200 ms; seven tools discovered, all search/read; MCP enabled while Slack agent-app experience remains off |
| Inside Success Slack read smoke | Synthetic zero-match public-channel lookup succeeded; result content was not printed |
| Inside Success Slack negative write | `slack_send_message` unavailable and blocked; no Slack message or write request executed |
| Mitchell Slack strict OAuth | Exactly 14 reviewed read scopes granted with no missing scopes; token/client/meta state stored mode-600 outside Git |
| Mitchell Slack MCP inventory | Connected in 3,186 ms; seven exact search/read tools; Slack MCP enabled and agent-app experience off |
| Mitchell Slack read smoke | Synthetic zero-match channel search succeeded; 167-byte response hashed, source content not printed |
| Mitchell Slack negative write | `slack_send_message` absent from discovery and excluded locally; blocked before request, with no Slack write executed |
| Work Gmail OAuth/read smoke | Exact `gmail.readonly` token stored mode 600; `list_labels` metadata-only probe passed; four read tools exposed locally |
| Work Drive OAuth/read smoke | Exact `drive.readonly` token stored mode 600; bounded recent-file probe passed; four read tools exposed locally |
| Work Calendar OAuth/read smoke | Exact Calendar list/events read-only token stored mode 600; calendar-list probe passed; three read tools exposed locally |
| Work Google negative writes | Gmail draft/label writes, Drive create/copy/download, and Calendar create/update/delete/respond/suggest tools excluded; registry tests reject representative writes before request |
| Personal Gmail OAuth/read smoke | Isolated personal client; exact `gmail.readonly` token mode 600; `list_labels` metadata-only probe passed |
| Personal Drive OAuth/read smoke | Exact `drive.readonly` token mode 600; bounded recent-file probe passed without printing content |
| Personal Calendar OAuth/read smoke | Exact Calendar list/events read-only token mode 600; calendar-list probe passed after selecting only the two reviewed permissions |
| Personal Google negative writes | Same explicit Gmail/Drive/Calendar write exclusions as work; registry assertions reject representative personal writes before request |
| Prompt 4 real acceptance | Cross-context, project resumption, and Inside Success report draft accepted with all claims cited and no reported leakage; focused Mitchell query timed out; Google/current-day cases failed closed |
| Codex classification | Unknown reduced from 49.1244% to 47.0728% by one verified workspace rule; 198 records changed; ambiguous projects remain unknown |
| Acceptance resources | Repeated project-resumption case passed in 103.8 s; maximum RSS 175,472,640 bytes (about 167.3 MiB) |
| Representative model quality | Six of six bounded tasks passed deterministic grounding/misattribution criteria; Flash retained as default because Luna tied quality at about 14x cost |
| Public web/shopping | Six cited search results and one official product-page fetch; URL/date/hash/untrusted labels present; browser/cart/checkout/payment unavailable |
| Google freshness | Work and personal each use one exact-scope offline grant. Both forced refreshes passed, all six standard-API metadata smokes passed, and startup/direct calls refresh automatically. Personal returned no refresh-token lifetime field after the app moved to In production. |
| Personal Google direct acceptance | The MCP probe now rejects protocol error blocks instead of reporting false success. Standard Gmail, Drive, and Calendar APIs returned bounded metadata successfully through host-locked GET-only tools. Personal-obligations acceptance passed with 6/6 cited claims, 5 confirmed and 1 inferred, mixed evidence labeled, no reported leakage, 68.4 s latency, and $0.00308 estimated model cost. |
| Zoom OAuth/inventory/read acceptance | Secretless public-client PKCE succeeded with exactly four read scopes and refreshable owner-only token state. Shared-access widening stayed unchecked. Live discovery found 12 raw tools, including two writes that are filtered out; four reviewed reads are exposed. After a metadata-only smoke, a bounded recent work-meeting case passed with 3/3 cited confirmed claims, no reported leakage, 65.5 s latency, and $0.00523 estimated model cost. |
| Hermes voice runtime | Corrected orchestrator from unused `.venv` to actual `venv`; deliberate microphone → local faster-whisper → DeepSeek Flash → audible Edge TTS loop passed |
| Hermes voice choice and latency | Syed selected `en-GB-RyanNeural`; first/repeat direct synthesis measured 2.04/1.43 s; bounded 1.5 s early-stop and zero-volume playback exited cleanly |
| Hermes automatic TTS and barge-in | Corrected `voice.auto_tts` from false to true after an owner-only backup; MacBook-speaker reply was audible. After the process-local macOS fallback guard, the corrected no-headphones retest interrupted playback at 14:52:50 and Syed confirmed Ryan stopped immediately, accepted the correction, and did not replay. Continuous listening remained active as designed; a later “great” → “grade” local-Whisper error is retained as an STT limitation. Overlay buttons remain. |
| One-shot screen and Luna | Syed selected one Codex region through Apple's visible UI; Luna succeeded in 4,948 ms with 3,549 input/256 output tokens and estimated $0.005085 cost. No continuous capture, Accessibility, or computer control. macOS toolbar destination drift required one fixed quarantine recovery; after exact confirmation, only that screenshot was permanently deleted and Finder showed the other six Trash items remained. No raw acceptance screenshot remains. |
| Daily launcher and overlay controls | Foreground launcher health, visible transcript/status/context, Mute, Unmute, active-turn Cancel, and Dismiss passed. Cancel interrupted a harmless active Flash API call after about seven seconds without a follow-up turn. Approve stayed disabled without an exact preview hash. Control audit was owner-only; no service, broad process target, external action, or launch agent was created. |

Runtime data, audio, checkpoints, restore files, private evidence, and diagnostics are excluded from Git.

## Cost baseline

The measured DeepSeek connectivity tests cost less than `$0.00005` combined. A planning scenario of 20 million routine input tokens and 4 million routine output tokens per month is about `$3.92` at the checked Flash prices. Adding 100,000 Luna input tokens/20,000 output tokens and 20,000 Terra input tokens/5,000 output tokens adds roughly `$0.35`, for an illustrative model total near `$4.27/month`. Edge TTS and local faster-whisper have no per-request API charge. Actual use, cache pricing, connector plans, and provider price changes can materially change this estimate; the runtime warning/soft/hard thresholds remain `$25/$40/$50`.
