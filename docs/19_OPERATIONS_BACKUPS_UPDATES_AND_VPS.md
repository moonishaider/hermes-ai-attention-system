# Operations, Backups, Updates, and VPS

## Local operation

Initial runtime on the Mac:

- Hermes Desktop/runtime;
- small plugins/adapters;
- SQLite/FTS state;
- overlay;
- history bridge;
- browser/screen bridge;
- logs/audit.

Use launch-at-login only after explicit approval and stability testing. Do not install hidden background services during development.

## Resource management

For 8 GB RAM:

- API-hosted models;
- cloud STT initially;
- no local LLM;
- no local Postgres;
- no unnecessary Docker;
- bound caches and worker concurrency;
- one Hermes runtime/profile;
- lazy-load specialists;
- close idle browser automation sessions;
- monitor memory, CPU, swap, and disk.

Quality should be preserved through API use and retrieval design, not by loading everything locally.

## Health checks

Expose:

- Hermes/runtime status;
- connector authentication/freshness;
- last successful sync;
- history bridge checkpoint;
- queue depth;
- action executor enabled/disabled;
- monthly cost;
- storage/backup status;
- model/provider health;
- recent errors.

## Backups

Back up:

- configuration without secrets;
- SQLite databases;
- specialist definitions;
- memory/task state;
- context rules;
- audit/usage metadata;
- selected imported evidence if retention permits.

Requirements:

- encrypted;
- versioned;
- restorable;
- tested;
- not stored in the source repository;
- retention schedule.

## Updates

Pin a stable Hermes version for production.

Before an update:

1. read official changelog/security notes;
2. snapshot config/state;
3. test in a separate environment/branch;
4. rerun tool inventory and permissions;
5. rerun acceptance/security tests;
6. verify memory/database migrations;
7. roll out with rollback path.

Never auto-install skills or major Hermes updates.

## Logging

- structured and redacted;
- do not log raw tokens, credentials, full sensitive messages, or browser cookies;
- correlation IDs for queries/actions;
- configurable retention;
- diagnostic bundle excludes secrets;
- user-visible audit for external actions.

## Optional VPS decision

Only add a VPS after measuring:

- how often the Mac is asleep/offline;
- missed messages/meetings/briefings;
- whether always-on collection changes behavior;
- incremental cost and security burden.

Use a small CPU VPS for read-only/scheduled components. Encrypt transit and state. Keep action credentials and computer control local where possible.

## Disaster recovery

Document:

- start in safe/read-only mode;
- restore last known database snapshot;
- revoke connector tokens;
- disable executor;
- rebuild evidence index;
- reauthorize accounts manually;
- verify integrity and acceptance tests before re-enabling writes.
