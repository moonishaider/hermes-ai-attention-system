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
| Real Codex bounded ingestion | 12,000 scanned; 1,842 conversation items; 469 Inside Success; tool output/reasoning excluded |
| Codex ingestion resources | 2.10 s; peak 117.9 MB |
| SQLite backup to new file | Integrity `ok`; 1,842 evidence rows |
| Screen adapter | Grant and single-use semantics passed; OS permission not requested |
| Supervised action | Kill switch, destination, approval/hash, and negative destination tests passed with synthetic sender |
| Provider routes | Contract tests passed; credentialed live smokes pending |
| Connector inventories | Disabled with allowlists; live OAuth/tool-list smokes pending |

Runtime data, audio, checkpoints, restore files, private evidence, and diagnostics are excluded from Git.
