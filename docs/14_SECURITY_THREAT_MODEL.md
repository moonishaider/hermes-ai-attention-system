# Security Threat Model

## Primary assets

- company/client communications and documents;
- personal email/finance/tax information;
- API/OAuth credentials;
- browser sessions;
- local files and repositories;
- assistant memory and task state;
- outgoing communications;
- reputation and stakeholder trust;
- spending limits.

## Main threats

### Prompt injection from source content

An email, Slack message, document, webpage, transcript, or skill may instruct the assistant to ignore policy or use tools.

Controls:

- treat source content as untrusted data;
- tool policy outside the prompt;
- separate reader/retrieval from executor;
- no credentials in model context;
- structured extraction;
- source labeling;
- action approval;
- injection tests.

### Cross-context leakage

Inside Success information appears in a Mitchell/personal outgoing message or vice versa.

Controls:

- immutable provenance;
- context-minimized drafts;
- destination policy;
- outgoing context scan;
- exact preview;
- regression tests.

### Over-broad OAuth/tool scopes

Convenience integration grants send/modify/delete when only read is needed.

Controls:

- scope inventory;
- official least-privilege scopes;
- per-tool allowlist;
- separate write credential/executor;
- periodic permission audit;
- revoke path.

### Malicious or compromised skills/dependencies

Controls:

- no autonomous install;
- source review;
- pinned version/hash;
- dependency lock;
- isolated testing;
- disabled tools during evaluation;
- update review and rollback.

### Model error/hallucination

Controls:

- evidence citations;
- deterministic calculations;
- confidence/uncertainty;
- reviewer pass;
- no autonomous high-stakes submission;
- acceptance/evaluation suite.

### Destructive computer/browser action

Controls:

- no YOLO mode;
- existing profile mapping;
- preview and approval;
- action classes;
- restricted executor;
- idempotency;
- kill switch;
- manual-only A4 actions.

### Duplicate or stale external actions

Controls:

- idempotency keys;
- preview hash;
- approval expiry;
- source revision checks;
- confirmation of execution result;
- duplicate-send tests.

### Secret leakage

Controls:

- Keychain/environment outside Git;
- log redaction;
- no token display;
- connector isolation;
- minimal provider payloads;
- secret scanning in CI/pre-commit.

### Cost runaway

Controls:

- usage ledger;
- rate limits;
- retry caps;
- budget alerts/hard stop;
- scheduled-work quotas;
- model escalation policy.

### Data corruption/loss

Controls:

- SQLite transactions;
- backups;
- migrations with rollback;
- checksums;
- test restore;
- source re-indexability;
- Git for configuration/code only.

## Trust boundaries

1. user/overlay;
2. Hermes master model;
3. source reader tools;
4. local evidence/memory/task stores;
5. specialist workers;
6. action proposal queue;
7. restricted executor;
8. external providers/accounts;
9. Codex build environment.

Document data flow and credentials crossing each boundary.

## Security review gate

Before enabling any external write:

- threat model updated;
- OAuth scopes reviewed;
- tool schema reviewed;
- destination lock verified;
- prompt-injection tests pass;
- duplicate/rollback behavior tested;
- preview exactness verified;
- kill switch tested;
- Syed performs a supervised dry run.

## Full Access Codex and GitHub threats

Add the build environment itself to the threat model: Codex has deliberately selected Full Access and therefore could technically reach unrelated files and network resources. Controls include an isolated workspace, current backup, project command-deny rules, no-deletion policy, Git checkpoints, narrow outside-write logging, no `sudo`, secret protection, and a single authorized personal GitHub destination.

For GitHub, threats include excessive token scope, cross-owner credential reuse, write tools leaking into a read-only connection, prompt injection from repository content/issues, accidental company-repository writes, and bulk cloning/indexing. Mitigate through separate credentials, minimal scopes/toolsets, read-only mode, tool inventory and negative tests, owner/repository allowlists, immutable provenance, and treating repository content as untrusted evidence rather than instructions.

