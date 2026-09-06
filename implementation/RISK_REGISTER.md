# Risk Register

## Current candidate risks — 5 September 2026

These entries supplement and supersede conflicting prototype assumptions below.
See [compatibility and activation limits](CANDIDATE_COMPATIBILITY_2026-09-05.md).

| Risk | Current control | Remaining verification |
|---|---|---|
| Public repository leakage | Exact public destination, reviewed branch/commit, actual committed-blob scanning and private exclusions. | Run publication guards on the final candidate. |
| Duplicate action after crash or cancellation | Durable native action claims, canonical terminal authority, read-only outcome reconciliation and no automatic replay of unknown outcomes. | Packaged interruption and recovery acceptance. |
| Browser authority or account confusion | Native selected-target binding, configured identity provenance, fresh observations and scoped owner task grants; normal driver permissions. | Runtime driver currently reports pending OS permission. Page markers alone do not prove account identity. |
| Browser network containment | Backend fetch validates and pins public destinations; browser navigation validates proposed/observed scope. | Native browser subresource and redirect containment is not verified. |
| App replacement loses OS grants | Preserve original signed app; verify replacement identity and retain rollback. | Ad-hoc signature changes can require normal owner consent. |
| Dependency or database regression | Isolated locked environment, copy-based integrity/restore proof, code-only rollback and final-path venv creation. | Installed health and provider acceptance after activation. |

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
