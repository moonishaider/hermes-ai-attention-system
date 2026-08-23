# Prompt 8 Jarvis storage audit

Date opened: 2026-08-23
Exact pre-cleanup measurement: 2026-08-24 (Asia/Karachi)

No Prompt 8 cleanup has occurred. Measurements below are the exact current pre-cleanup baseline after installing commit `af8ee1128ea472ed1a5316eae99b9cc443a70659`.

| Exact path | Initial size | Classification |
|---|---:|---|
| Repository root | 13,748,504 KB | Active project plus reproducible build output and historical rollbacks; retain until acceptance |
| `/Applications/Jarvis.app` | 6,020 KB | Active product; retain |
| `~/.hermes/jarvis-runtime` | 67,372 KB | Active runtime/database/code; retain |
| Entire `~/.hermes` | 15,588,104 KB | Shared Hermes runtime, connectors, tokens, memory, skills, histories, and state; never broad-delete |
| `jarvis/src-tauri/target` | 10,446,496 KB | Reproducible Rust build output; largest safe candidate after acceptance |
| `.tooling` | 1,100,568 KB | Project-local pinned Node/Rust/Cargo toolchains; reproducible but useful for rollback/rebuild |
| `backups` | 1,956,428 KB | Mixed required and obsolete rollbacks; exact-manifest review required |
| `jarvis/node_modules` | 123,656 KB | Lockfile-reproducible project dependency tree |
| `runtime-data` | 62,584 KB | Active/private project runtime material; retain |
| `.workspace-quarantine` | 43,880 KB | Already quarantined recoverable project artifacts; retain under current policy |
| `.git` | 8,948 KB | Active rollback/history; retain |
| `jarvis/dist` | 312 KB | Reproducible frontend bundle |

## Candidate detail (no action taken)

- Rust target output: 8,631,440 KB debug plus 1,815,040 KB release.
- Project toolchains: 576,320 KB Rustup, 324,232 KB Cargo, 199,964 KB Node, and 44 KB npm cache.
- Historical application rollbacks: 49 top-level `.app` bundles totaling 291,464 KB. At least the Prompt 8 baseline, immediately preceding app, and final accepted rollback must remain.
- Database rollback files: 23 top-level `.sqlite3` files totaling 1,184,880 KB. Current, Prompt 8 pre-change, pre-install, and final accepted restore copies must remain; older duplicates require hash/necessity review before quarantine.
- Active installed idle footprint at measurement: Jarvis 15,520 KB RSS and its exact owned Hermes gateway 57,840 KB RSS (73,360 KB combined); CPU was approximately 0.4% combined.

## Cleanup gate

Cleanup may begin only after the installed Prompt 8 app passes acceptance and a current rollback is retained. Candidates must be individually measured and proven redundant/reproducible. Current app/runtime/database/secrets/history/memory and unrelated computer files are prohibited targets.

The Prompt 8 text asks for an executing cleanup script, but `AGENTS.md` line 63 and `docs/15_CODEX_EXECUTION_SAFETY.md` lines 37 and 61 explicitly forbid deletion through Python, Node, shell, Git, package managers, or indirect helpers and require project-local quarantine plus a committed deletion plan. Those higher-priority project boundaries remain mandatory. Therefore this milestone may produce an exact generated manifest and reversible quarantine operation only; it will not claim quarantined bytes as freed disk space. Any later physical deletion requires a separately authorized workflow that changes neither these safety controls nor the current product state.
