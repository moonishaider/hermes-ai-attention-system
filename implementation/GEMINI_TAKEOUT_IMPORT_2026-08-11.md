# Gemini Takeout Import

**Completed:** 11 August 2026

**State:** Live in the owner-local Hermes runtime database

**Rollback checkpoint:** `d740478`
**Raw archive:** Remains in the owner's Downloads folder and is not tracked by Git

## Outcome

Hermes now supports bounded historical ingestion from an official Google Takeout Gemini export. The imported material is searchable evidence, not trusted instructions or durable memory. The implementation performs no Google account write, OAuth change, browser control, message send, attachment execution, or continuous synchronization.

The accepted import inserted 178 evidence records. An immediate rerun inserted zero records and reported all 178 as duplicates.

## Inspected archive

- ZIP size: 189,273,518 bytes.
- ZIP SHA-256: `8c70237bf402919639e5fe27811c41d5fd41d4c9b6a513becbec0e186fefb2f4`.
- ZIP integrity: CRC validation passed.
- Archive inventory: 408 regular entries and 278,202,527 uncompressed bytes.
- Gemini Apps activity records: 1,178 total; dated range 13 February 2025 through 20 June 2026 UTC.
- Selected cutoff: 1 November 2025, matching the owner's stated useful Gemini-use window.
- Selection: 1,175 activities, including 14 without exported timestamps; three older activities skipped.
- Grouping: 176 conversation or standalone activity evidence records plus two Gemini-native metadata pages.
- Ignored by design: 378 binary attachments and 27 other Takeout entries outside the reviewed Gemini pages.

No raw conversation text, attachment name, email content, credential, or private diagnostic payload is recorded in this implementation report.

## Supported schema and safety controls

The importer accepts an official ZIP containing the exact Gemini Apps activity member and optionally the two reviewed Gemini-native metadata pages. It validates archive size, entry count, total expanded size, member size, CRC integrity, duplicate member names, encryption, symlinks, absolute paths, traversal paths, and backslash-based paths before parsing.

Only these inert HTML inputs are parsed:

- `Takeout/My Activity/Gemini Apps/My Activity.html`
- `Takeout/Gemini/gemini_gems_data.html`
- `Takeout/Gemini/gemini_scheduled_actions_data.html`

The archive is never extracted. Scripts are discarded by the inert parser. Binary attachments are neither read into evidence nor retained by Hermes. Every record passes secret redaction and prompt-injection detection before insertion. Credential-shaped OpenAI, DeepSeek, GitHub, Slack, AWS, and private-key material is redacted by the shared security layer.

Import requires `--confirmed`; preview alone cannot modify the database. Content is never promoted automatically to tasks, memories, skills, or context-routing facts.

## Provenance and classification

Each imported record preserves:

- source system `gemini_export`;
- logical connection `gemini_official_takeout`;
- immutable Gemini chat or activity identifier;
- archive hash and exact archive member;
- exported activity start/end dates when available;
- record and ignored-asset counts;
- explicit `binary_attachments_ingested: false`;
- confirmed, inferred, or uncertain confidence state.

All 178 records remain in the `unknown` context. This is deliberate: historical Gemini use spans personal and professional topics, and ambiguous content must not be forced into a context merely to improve a metric. Of the imported records, 161 are inferred and 17 uncertain. Uncertain records include detected prompt-injection text or conversations whose dates had to be inferred from the archive because Google exported no timestamp.

## Acceptance evidence

- Preview: 0.79 seconds; approximately 103.5 MiB maximum RSS.
- Confirmed import: 2.00 seconds; approximately 107.5 MiB maximum RSS.
- Inserted: 178; duplicates on first run: zero.
- Duplicate rerun: inserted zero; duplicates 178.
- Search: source-filtered full-text retrieval returned Gemini evidence.
- Database: SQLite integrity check returned `ok`.
- Redaction audit: no precise provider-key or Slack-token pattern remained in imported content.
- Injection handling: 12 imported evidence groups were marked uncertain rather than trusted.
- Health: Gemini state reports `imported`, 178 records, continuous sync false, and binary attachments ingested false.
- Regression: all 70 project tests, configuration doctor, secret scan, bytecode compilation, and whitespace checks pass.
- External writes: none.

## Backup and rollback

Before import, the runtime database was copied with the project backup tool to:

`backups/hermes-attention-before-gemini-import-20260811T190000Z.sqlite3`

The backup is ignored by Git, has SHA-256 `1ff1ded1d970a032b16eeb94ad77b6287112a6480e275f023de187234a970c67`, restored successfully to a separate in-memory database, and contains zero Gemini records.

For code rollback, normally revert the Gemini implementation commit or return to checkpoint `d740478`; do not rewrite history. For data rollback, first quit Hermes, preserve the current database as another non-overwriting backup, restore the dated pre-import backup to a new file, verify SQLite integrity, and only then perform a controlled replacement. The raw Takeout archive is not required for rollback.

## Known limitations

- Google provides no supported continuous personal Gemini-history API; future updates require another official Takeout export and confirmed incremental import.
- Binary uploads and generated media are intentionally excluded.
- The importer does not reconstruct every visual nuance of the original Gemini UI.
- Undated exported activities retain honest inferred timestamps and uncertain confidence.
- The 178 records remain Unknown until optional owner-reviewed semantic calibration; explicit Gemini or cross-context searches are therefore the reliable retrieval path.
