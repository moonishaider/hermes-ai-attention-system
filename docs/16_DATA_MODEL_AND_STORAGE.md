# Data Model and Storage

This is a logical model. Codex should adapt it to verified Hermes storage/plugin interfaces and avoid duplicating native structures unnecessarily.

## Core entities

### Context

- `context_id`
- `name`
- `type`
- `status`
- `parent_id` optional
- browser profile mapping
- default policy
- aliases/rules

### SourceConnection

- `connection_id`
- provider/system
- account/workspace identity
- context defaults
- credential reference (never secret value)
- scopes/tool inventory
- status/freshness
- connector version

### EvidenceItem

- `evidence_id`
- connection/source IDs
- native item ID/revision
- timestamp/ingested timestamp
- author/participants
- title/summary/content reference
- content hash
- raw-retention status
- source URL/path/session reference
- context labels/confidence
- sensitivity
- extraction status

### MemoryRecord

- `memory_id`
- statement/structured fact
- namespace
- context
- status: proposed/confirmed/superseded/rejected
- evidence links
- confidence
- created/confirmed/review dates
- contradiction set
- produced-by module/model/version

### Task/OpenLoop

- `task_id`
- title/description
- context/project
- type: task/commitment/question/blocker/decision/follow-up
- status/priority
- owner/waiting-on
- due date
- evidence links
- confidence
- source candidate vs confirmed
- board/tenant label
- audit history

### SpecialistDefinition

- ID/version/status
- activation rules
- instructions/skill reference
- tool policy
- memory namespace
- source policy
- model/reviewer policy
- schemas/templates/tests

### ActionProposal

- proposal ID
- action/risk class
- context
- target/destination
- exact payload
- browser profile/account
- source request/evidence
- preview hash
- idempotency key
- approval state/expiry
- execution result
- audit timestamps

### AuditEvent

- event ID/time
- actor/component/model
- operation
- affected record/action
- context
- outcome
- redacted metadata
- correlation ID

### UsageEvent

- provider/model
- feature/specialist/context
- tokens/cost
- latency
- success/error
- timestamp

## Storage recommendation

Initial:

- Hermes-native compact user/memory mechanism;
- Hermes Kanban/current equivalent for tasks where it can carry required metadata;
- one local SQLite database for integration metadata, evidence index, approvals, audit, usage, and bridge checkpoints;
- SQLite FTS5 for local text retrieval;
- files/object references for large raw exports, encrypted/permission-restricted and outside Git.

Avoid:

- local Postgres;
- multiple database services;
- a vector database before testing;
- duplicate copies of every remote message;
- secrets in SQLite.

## Encryption and permissions

- local OS file protections;
- secrets in Keychain/environment/credential manager;
- optional encrypted raw-data directory;
- runtime data directory excluded from Git;
- backups encrypted;
- separate write executor credential store.

## Migrations

- versioned;
- backward-compatible where possible;
- dry-run and backup;
- rollback or restore procedure;
- migration tests with representative fixtures.

## Indexing

- incremental checkpoints per source;
- idempotent upsert;
- revision detection;
- deduplication;
- content normalization;
- alias/entity extraction;
- context classification;
- candidate tasks/memories;
- audit.

## Deletion/re-indexing

Support:

- remove by source connection;
- remove by date range;
- remove by context;
- remove raw content but retain minimal audit;
- rebuild FTS/derived data from source;
- invalidate memories dependent on removed evidence.

## GitHub evidence fields

Support optional GitHub fields on evidence records: connection ID, owner, repository, visibility, object type, branch, commit SHA/object ID, path, line range, issue/PR/discussion number, actor, created/updated timestamps, and retrieval freshness. Do not duplicate full repository contents by default; cache only normalized metadata, selected evidence, and retrieval checkpoints.

