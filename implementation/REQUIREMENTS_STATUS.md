# Requirements Status

| Group | Status | Evidence |
|---|---|---|
| PRD-001–010 | Partial | One Hermes plugin and working local core; provider/voice acceptance is manual |
| CTX-001–008 | Implemented locally | Provenance-first multi-label router, profile metadata, fail-closed action policy |
| SRC-001–012 | Partial | Codex, ChatGPT export/relay, and GitHub adapters implemented; live OAuth sources disabled |
| MEM-001–012 | Implemented locally | SQLite/FTS evidence, proposed memory, tasks, audit, checkpoints, contradictions |
| SPC-001–008 | Implemented | Persistent registry, five examples, disabled serious-mode module, reusable template/scaffolder |
| ATT-001–010 | Partial | Ranked queue, handoff, report draft, explicit screen request, optional overlay; manual acceptance pending |
| MOD-001–011 | Implemented as policy | Approved routes, usage ledger, warning/hard budgets; credentialed API smoke tests pending |
| ACT-001–012 | Preview/shadow complete | Exact hash, TTL, idempotency, context/profile/risk policy, kill switch; executor intentionally absent |
| OPS-001–010 | Partial | Baseline, scripts, tests, runbooks, secret scan; recovery and connector drills manual |
| GIT-001–009 | Partial | Separate owner-bound read-only configs, provenance, negative tests; live MCP smoke test pending |
| CDX-001–005 | Implemented | Protected controls, baseline commit `b8e8a6e`, implementation records, incremental ingestion |

Completion requires code/configuration plus test evidence or an explicitly documented manual operational proof.

Current automated evidence: 14 passing stdlib `unittest` cases; configuration doctor, repository secret scan, `git diff --check`, safety preflight, and safety-control verifier. See `implementation/MILESTONE_01_WORKING_CORE.md`.
