# Requirements Status

| Group | Status | Evidence |
|---|---|---|
| PRD-001–010 | Partial operational | Installed Hermes, live project toolset, safe launcher, provider routes and six remote logical connector groups live; real daily-use, voice, and screen acceptance pending |
| CTX-001–008 | Implemented locally | Provenance-first multi-label router, profile metadata, fail-closed action policy |
| SRC-001–012 | Partial operational | Codex ingestion is real-data tested; GitHub/Slack/Google are live but metadata-smoked; ChatGPT importer awaits requested export; Zoom remains externally blocked and disabled |
| MEM-001–012 | Implemented locally | SQLite/FTS evidence, proposed memory, tasks, audit, checkpoints, contradictions |
| SPC-001–008 | Implemented | Persistent registry, five examples, disabled serious-mode module, reusable template/scaffolder |
| ATT-001–010 | Partial operational | Queue, handoff, report, overlay controls, one-shot screen adapter; macOS capture acceptance pending |
| MOD-001–011 | Operational | Native DeepSeek Flash plus direct Pro/Luna/Terra all passed live synthetic smokes; Sol remains builder-only; usage/cost ledger active |
| ACT-001–012 | Restricted executor in shadow | Exact hash, TTL, idempotency, context/risk policy, kill switch, fixed Slack destination; no executor exposed to Hermes |
| OPS-001–010 | Partial operational | Resumable onboarding, exact install, backups, restore drill, resource evidence, 30 tests; Prompt 4 acceptance, Zoom, ChatGPT export, and macOS microphone/screen gates remain |
| GIT-001–009 | Operational | Private project published; separate personal and Inside Success MCPs live through `/readonly`, exact allowlists, metadata smokes, immutable provenance adapter, and negative write proof |
| CDX-001–005 | Implemented | Protected controls, baseline commit `b8e8a6e`, implementation records, incremental ingestion |

Completion requires code/configuration plus test evidence or an explicitly documented manual operational proof.

Evidence-level definitions and the current dated truth are in `implementation/CURRENT_OPERATIONAL_STATE.md`; this table is requirement-group rollup only.

Current automated evidence: 30 passing tests; configuration doctor, secret scan, diff check, safety verification, synthetic voice, real bounded Codex ingestion, backup integrity drill, two isolated Slack connectors, and six isolated work/personal Google read-only resource connectors. The onboarding state distinguishes completed dependencies from the ChatGPT export and macOS permission gates and reports Zoom as the sole pending remote connector. See `implementation/OPERATIONAL_TEST_EVIDENCE.md`.
