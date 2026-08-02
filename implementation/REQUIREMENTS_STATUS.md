# Requirements Status

| Group | Status | Evidence |
|---|---|---|
| PRD-001–010 | Partial operational | Safe daily launcher, source-backed resumption/report/cross-context use, and public research pass; voice, screen, Google-dependent daily use, and external actions remain gated |
| CTX-001–008 | Implemented locally | Provenance-first multi-label router, profile metadata, fail-closed action policy |
| SRC-001–012 | Partial operational | Codex/GitHub/Slack and public web have bounded real acceptance; Google tokens require reauthorization; ChatGPT awaits export; Zoom TLS recovered but OAuth is pending |
| MEM-001–012 | Implemented locally | SQLite/FTS evidence, proposed memory, tasks, audit, checkpoints, contradictions |
| SPC-001–008 | Implemented and tested | Persistent loading, context restrictions, namespace-scoped memory, disabled serious mode, five examples, and reusable scaffolder |
| ATT-001–010 | Partial operational | Queue, handoff, report, overlay controls, one-shot screen adapter; macOS capture acceptance pending |
| MOD-001–011 | Operational | Flash/Pro/Luna/Terra passed representative bounded tasks; Flash retained on equal routine score and much lower cost; Sol remains builder-only |
| ACT-001–012 | Restricted executor in shadow | Exact hash, TTL, idempotency, context/risk policy, kill switch, fixed Slack destination; no executor exposed to Hermes |
| OPS-001–010 | Partial operational | Resumable onboarding, daily health/overlay launcher, backups, restore drill, 39 tests, and 167.3 MiB acceptance peak; human permission/account gates remain |
| GIT-001–009 | Operational | Private project published; separate personal and Inside Success MCPs live through `/readonly`, exact allowlists, metadata smokes, immutable provenance adapter, and negative write proof |
| CDX-001–005 | Implemented | Protected controls, baseline commit `b8e8a6e`, implementation records, incremental ingestion |

Completion requires code/configuration plus test evidence or an explicitly documented manual operational proof.

Evidence-level definitions and the current dated truth are in `implementation/CURRENT_OPERATIONAL_STATE.md`; this table is requirement-group rollup only.

Current evidence is summarized in `implementation/PROMPT_04_ACCEPTANCE_REPORT.md`: 39 passing tests, safety/config/secret checks, bounded real-data cases, representative model evaluation, classification calibration, public-web acceptance, backup/restore, and resource accounting. Google, Zoom, ChatGPT export, microphone, screen, and exact Slack destination/action approval remain explicit gates.
