# Prompt 8 Jarvis storage audit

Date opened: 2026-08-23
Exact pre-cleanup measurement: 2026-08-24 (Asia/Karachi)

No Prompt 8 cleanup has occurred. Measurements below are the exact current pre-cleanup baseline, refreshed after installing commit `8866bd1194d86d96f1ca087336265f9caa1209b8`.

| Exact path | Initial size | Classification |
|---|---:|---|
| Repository root | 14,159,236 KB | Active project plus reproducible build output and historical rollbacks; retain until acceptance |
| `/Applications/Jarvis.app` | 6,052 KB | Active product; retain |
| `~/.hermes/jarvis-runtime` | 67,424 KB | Active runtime/database/code; retain |
| Entire `~/.hermes` | 15,588,104 KB | Shared Hermes runtime, connectors, tokens, memory, skills, histories, and state; never broad-delete |
| `jarvis/src-tauri/target` | 10,714,820 KB | Reproducible Rust build output; largest safe candidate after acceptance |
| `.tooling` | 1,100,568 KB | Project-local pinned Node/Rust/Cargo toolchains; reproducible but useful for rollback/rebuild |
| `backups` | 2,098,412 KB | Mixed required and obsolete rollbacks; exact-manifest review required |
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

## Policy-compliant quarantine tool

`scripts/safe_quarantine_jarvis_artifacts.py` implements the permitted operation without a deletion mode. It accepts only these exact project-owned, reproducible candidates:

- `jarvis/src-tauri/target`
- `jarvis/dist`
- `jarvis/node_modules`
- `.tooling/npm-cache`

The tool creates an owner-only manifest under ignored `runtime-data/storage-manifests/`, records byte/object counts plus a deterministic metadata SHA-256, revalidates every entry immediately before action, rejects top-level, broken, absolute, or escaping symlinks plus path escapes/protected paths/tampering, and hashes safe internal dependency links without following them. It moves exact candidates only to a recoverable `.workspace-quarantine/prompt8-storage-<manifest-id>` destination. Dry-run and quarantine behavior are covered by `tests/test_prompt8_storage.py`. It reports `freed_bytes=0` because project-local quarantine does not release filesystem space. No real candidate has been quarantined yet; execution remains gated on final installed acceptance.

The current real four-candidate plan and dry-run passed with manifest ID `2d680dac73177bef`, four exact entries, 16,873,798,593 candidate bytes, owner-only mode `0600`, and zero moved or freed bytes. This proves the plan against the installed `8866bd1` dependency/build trees without changing them; it must be regenerated if a later rebuild changes candidate metadata.
