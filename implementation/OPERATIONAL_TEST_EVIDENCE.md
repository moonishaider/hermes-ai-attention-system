# Operational test evidence

Checked: 1 August 2026

| Check | Result |
|---|---|
| Safety preflight, persisted hook tests, command-rule tests | Passed |
| Python unit, integration, security, history, action, model-route tests | 25 passed |
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
| Connector inventories | Disabled with allowlists; live OAuth/tool-list smokes pending |

Runtime data, audio, checkpoints, restore files, private evidence, and diagnostics are excluded from Git.

## Cost baseline

The measured DeepSeek connectivity tests cost less than `$0.00005` combined. A planning scenario of 20 million routine input tokens and 4 million routine output tokens per month is about `$3.92` at the checked Flash prices. Adding 100,000 Luna input tokens/20,000 output tokens and 20,000 Terra input tokens/5,000 output tokens adds roughly `$0.35`, for an illustrative model total near `$4.27/month`. Edge TTS and local faster-whisper have no per-request API charge. Actual use, cache pricing, connector plans, and provider price changes can materially change this estimate; the runtime warning/soft/hard thresholds remain `$25/$40/$50`.
