# Prompt 8 Jarvis storage audit

Date opened: 2026-08-23
Exact pre-cleanup measurement: 2026-08-24 (Asia/Karachi)
Exact quarantine and post-check: 2026-08-25 (Asia/Karachi)

The table below preserves the exact pre-cleanup baseline. After final installed voice acceptance and non-overwriting backups, four allowlisted reproducible build paths were moved to recoverable project-local quarantine. No file was permanently deleted and no unrelated path was touched.

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

## Candidate detail before quarantine

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

The tool creates an owner-only manifest under ignored `runtime-data/storage-manifests/`, records byte/object counts plus a deterministic metadata SHA-256, revalidates every entry immediately before action, rejects top-level, broken, absolute, or escaping symlinks plus path escapes/protected paths/tampering, and hashes safe internal dependency links without following them. It moves exact candidates only to a recoverable `.workspace-quarantine/prompt8-storage-<manifest-id>` destination. Dry-run and quarantine behavior are covered by `tests/test_prompt8_storage.py`. It reports `freed_bytes=0` because project-local quarantine does not release filesystem space.

## Executed recoverable quarantine

The final real plan, dry-run, and quarantine all passed with manifest ID `15745f4bb900c021`, owner-only manifest `runtime-data/storage-manifests/prompt8-final-433484b-20260825T0212Z.json`, and these exact source paths:

- `jarvis/dist`
- `jarvis/node_modules`
- `.tooling/npm-cache`
- `jarvis/src-tauri/target`

The four entries totaled 18,378,960,151 logical bytes. The tool revalidated the manifest immediately before moving them to `.workspace-quarantine/prompt8-storage-15745f4bb900c021`; all four original paths are absent. This is recoverable quarantine on the same filesystem, so the exact freed space is **0 bytes**. APFS free-space changes are not attributed to this operation.

## Final retained footprint

| Exact path | Post-quarantine size | Result |
|---|---:|---|
| Repository root | 15,124,588 KB | Active source, Git, backups, runtime data, and recoverable quarantine retained |
| `/Applications/Jarvis.app` | 6,036 KB | Exact installed `433484b` product retained and healthy |
| `~/.hermes/jarvis-runtime` | 67,456 KB | Active runtime/database retained |
| Entire `~/.hermes` | 15,596,348 KB | Shared Hermes credentials, connectors, histories, memory, skills, and state retained |
| `.workspace-quarantine` | 11,348,468 KB | Recoverable quarantined build/dependency artifacts; same-volume bytes not freed |
| `backups` | 2,597,364 KB | Required app/database rollback copies retained |
| `runtime-data` | 62,608 KB | Active/private project runtime material retained |
| `.git` | 9,872 KB | Source history and rollback retained |

Final database safeguards were written to new paths before quarantine: `backups/prompt8-final-433484b-20260825T0210.sqlite3` (62,468,096 bytes, SHA-256 `8e6b7cb3916dd4ba19fd2aad37c10bfde85045bf85e9eb4c3f34c63f3915ad2d`) and `backups/prompt8-final-runtime-copy-433484b-20260825T0210.sqlite3` (66,473,984 bytes, SHA-256 `7d10bb000b852bfd07c81d2145e6c67aabe6ac8c5206647f206944d156510713`). Both return `PRAGMA quick_check=ok`. Current config/SOUL/USER state is retained in owner-only `~/.hermes/backups/prompt8-final-433484b-20260825T0210/`.

Post-quarantine checks confirmed the installed app and its owned gateway were still running, deep strict signature verification still passed, the installed SHA-256 was unchanged, runtime markers and plugin identity were correct, current and backup databases returned `quick_check=ok`, the required rollback app remained, and all files under `~/.hermes/credentials` and `~/.hermes/mcp-tokens` were owner-only mode `0600`.

Rollback is a move, not a rebuild: with Jarvis quit, move an exact quarantined entry back to its original marked-root path after first verifying that the original path is still absent and the manifest metadata matches. Never overwrite a newly created path.
