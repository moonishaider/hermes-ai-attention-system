# Codex Live Read-Only Synchronization — 6 August 2026

## Outcome

Hermes can now refresh recent Codex Desktop conversations without waiting for a
ChatGPT export, parsing an unstable transcript as the primary path, or running
a background service. Synchronization is local, incremental, explicitly
bounded, and read-only.

## User-visible behavior

- DLOA, worked-today/yesterday, latest-Codex, current-work, and
  project-resumption searches trigger a refresh before retrieval.
- `hermes_attention_daily_report` always refreshes Codex before creating its
  local draft.
- Attention includes **Sync latest Codex work** and shows the last checkpoint.
- The manual CLI diagnostic is `hermes-attention codex-sync`; it is not needed
  for ordinary use.
- Scheduling remains deliberately unimplemented. The previously discussed
  5:00 PM America/New_York fallback is only a future option.

## Security boundary

The subprocess argument vector is fixed to the resolved local Codex executable
plus `app-server`; no shell is used. Transport is stdio, not a network socket.
The hard method allowlist contains only `thread/list` and
`thread/turns/list`; full `thread/read` is excluded after its real response
sizes proved unnecessary and inefficient.
Negative tests reject `turn/start` and `thread/delete` before any I/O.

Summary turn pages preserve user and assistant text while omitting reasoning,
tool calls/results, commands, patches, and images. Remaining text is bounded,
secret-redacted, prompt-injection checked, and stored with immutable
thread/turn/item provenance and deterministic IDs. Raw private content remains
only in the ignored runtime database. No Slack message, Codex mutation,
external write, scheduler, daemon, watcher, or development server exists.

## Compatibility finding

The documented stable full-thread read is unsuitable for this real history:
five recent response sizes measured approximately 52.82, 85.95, 0.04, 46.65,
and 56.02 MiB. Official experimental `thread/turns/list` with summary view is
therefore the safe bounded current-work path. Because that method is
experimental, the existing accepted local JSONL importer remains the historical
fallback and the status surface reports the distinction honestly.

## Verification

- Marked-root preflight and safety controls passed before changes.
- The runtime database was backed up without overwrite at
  `backups/hermes-attention-before-codex-live-sync-20260805T221002Z.sqlite3`.
- Synthetic tests cover incremental checkpoints, provenance, redaction,
  reasoning/tool exclusion, non-read-method rejection, automatic current-work
  refresh, Desktop route shape, and UI availability.
- A real App Server sync completed successfully over stdio with no thread or
  external mutation. The real Hermes FastAPI worker route also completed with
  `external_writes=false` and `thread_mutations=false`; SQLite state is created
  and closed inside the same worker thread. The owner-visible DLOA after this
  implementation is the final usefulness acceptance.

## Rollback

Rollback checkpoint: `6f279aa` (`Checkpoint before live Codex synchronization`).
Revert the implementation commit normally; do not rewrite history. If local
runtime rollback is also required, restore the dated database backup to a new
file first and verify it before replacing any active state.
