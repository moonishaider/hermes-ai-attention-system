# Risk Register

| ID | Risk | Control | Status |
|---|---|---|---|
| R-001 | Full Access can reach unrelated local/network resources. | Marked-root preflight, trusted hooks, forbidden rules, protected safety files, Git checkpoints, no deletion. | Controlled, residual risk remains |
| R-002 | Source prompt injection activates tools or changes policy. | Treat source content as data; deterministic tool policy; action executor absent from Hermes surface; injection flags. | Implemented and unit tested |
| R-003 | Cross-context leakage in professional output. | Immutable provenance, deterministic multi-label classification, unknown/mixed fail closed, context-filtered retrieval. | Implemented; credentialed connector evaluation pending |
| R-004 | Over-broad connector credentials. | Read-only initial adapters, scope inventory, separate logical connections, manual OAuth review. | Manual gate |
| R-005 | Duplicate/stale external action. | Preview hash, expiry, idempotency key, destination/profile lock, kill switch; no executor in current build. | Implemented and unit tested |
| R-006 | Secret or real-data commit. | Ignore policy, synthetic fixtures, secret scanning, guarded push checks. | Active |
| R-007 | 8 GB Mac resource pressure. | SQLite/FTS, bounded batches, no dev server, no local LLM/Postgres/vector service. | Active |
| R-008 | Rapid Hermes/provider interface drift. | Target Hermes v0.19.1, capability matrix, adapter boundaries, fallbacks, pre-enable smoke tests. | Controlled; recurring verification required |
| R-009 | GitHub company write or wrong destination. | No runtime write tools; hooks deny mutation; guarded scripts allow personal project namespace only. | Active |
| R-010 | Unsupported continuous ChatGPT synchronization. | Official export plus explicit context relay; optional desktop capture remains disabled/experimental. | Active design constraint |
