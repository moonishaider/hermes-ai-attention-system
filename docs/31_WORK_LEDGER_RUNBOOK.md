# Work Ledger Runbook

**Operational since:** 12 August 2026

The Work Ledger is an incremental projection inside the existing project SQLite database. It does not create a second database and does not replace immutable evidence.

## Invariants

- Every ledger row links to at least one existing evidence row through `ledger_sources`.
- The fingerprint is deterministic, so retries are idempotent.
- Context-local dates use America/New_York for Inside Success and Mitchell, Asia/Karachi for Personal, and an explicit timezone for Mixed/Unknown.
- Actor state distinguishes owner, other person, and uncertain. Ambiguous records remain uncertain.
- Mitchell is dormant and excluded from ordinary queries unless explicitly requested.
- Collection cursors and run results live in `collection_runs` and `checkpoints`; connector rescans are not used as a substitute for incremental state.

## Initial migration result

On 12 August, the initial 11,395 existing evidence rows were projected in 16 batches of at most 750 with no skips. Subsequent bounded refreshes brought the ledger to 11,424 rows. The durable `work-ledger:evidence-v1` cursor makes later refreshes incremental.

## Recovery

Before Prompt 7, the database was copied to `backups/hermes-attention-before-prompt7-20260811T195914Z.sqlite3` with SHA-256 `57ef5fc8e84c4b51abe6f1aaadb08e502e86420f4a8bbfc291048289b40b4699`. A fresh pre-final copy was also created at `backups/prompt7-final-runtime-20260812T040344.sqlite3` and passed `PRAGMA integrity_check`. Restore only to a new file first, run SQLite integrity checks, then switch deliberately; never overwrite the only copy.
