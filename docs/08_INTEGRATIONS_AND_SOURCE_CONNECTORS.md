# Integrations and Source Connectors

## Decision hierarchy

1. verified Hermes native integration;
2. official provider MCP server;
3. audited maintained connector/skill with narrow scopes;
4. small custom adapter;
5. UI/browser automation only when no reliable API exists.

Do not begin with n8n or a custom FastAPI integration service. Syed does not own a personal n8n instance, and additional services create maintenance and permission complexity.

## Connector contract

Every connector must expose:

- connection identity and context mapping;
- exact OAuth/API scopes;
- read and write tool inventory;
- pagination and incremental checkpoint;
- rate-limit behavior;
- source freshness;
- provenance fields;
- content redaction hooks;
- health status;
- revoke/disconnect path;
- synthetic/mock mode;
- test evidence.

## Slack

Two independent connections/workspaces:

- Inside Success
- Mitchell

Initial tools:

- list/search/read permitted conversations;
- retrieve threads/replies;
- retrieve relevant files/metadata if allowed.

Initial external write tools are absent.

Later daily report write:

- separate credential/tool if practical;
- only one fixed Inside Success channel;
- exact preview and approval;
- idempotency key;
- no generic destination parameter exposed to the model.

The user may optionally communicate with Hermes in a private control DM/channel, but that does not grant broad posting authority.

## Google Workspace

Likely accounts:

- work Gmail/Calendar;
- personal Gmail/Calendar.

Verify the current state of:

- Hermes’s native Google Workspace skill;
- official Google Workspace MCP servers and their Developer Preview status;
- OAuth scope granularity;
- per-tool allowlists;
- account separation.

Use read-only Gmail/Calendar tools first. Never accept a full Google scope merely because a convenience setup requests it.

## Zoom

Use official Zoom MCP/native mechanisms when available and sufficiently scoped.

Desired reads:

- accessible meeting search;
- recordings;
- transcripts;
- meeting details;
- participants/ownership/group metadata.

The system may gather context from department meetings Syed did not attend, including while he was on holiday, when the configured credential permits access. Preserve provenance and do not infer Syed attended.

Support aliases `Syed` and likely transcription `Sid`.

## Codex

Local, read-only ingestion:

- discover `CODEX_HOME`;
- current official history/session/memory paths;
- repository/task metadata;
- Git status, diffs, commits, branches, and changed files;
- incremental checkpoints;
- no mutation.

Do not send full private code/history to unnecessary providers. Extract bounded summaries and evidence references.

## ChatGPT

- official export importer;
- date and conversation filters;
- watched context inbox;
- explicit context handoff from ChatGPT Work/desktop;
- optional explicit desktop UI capture adapter;
- periodic reconciliation.

No unsupported claim of continuous personal-history API.

## Files and documents

Allowlist selected roots/directories. Do not index the entire home folder.

Support:

- stable file ID/path;
- modified time/hash;
- context label;
- extraction status;
- retention;
- citation.

## Web research

Use a current web search backend through Hermes. Preserve URL, publication date, access date, source type, and confidence. High-stakes specialists prioritize primary sources.

## Screen

A local adapter creates a screenshot only after explicit activation. Store it temporarily unless the user explicitly saves/promotes it. Do not grant Accessibility/computer-control permission merely for screenshot reading.

## Fallback custom adapter

If a connector is required:

- implement against the internal `SourceAdapter` boundary;
- keep credentials outside the master model;
- use least-privilege scopes;
- expose only required operations;
- include mocks and contract tests;
- avoid a permanent FastAPI server unless remote access genuinely requires one.

## GitHub connectors

Add official GitHub MCP-based access as a first-class source. Configure separate read-only logical connections for `moonishaider` and `inside-success`, use minimal toolsets, preserve detailed provenance, and verify with negative tests that write/admin tools cannot execute. GitHub should support repository inventory, selected files/code, commits, issues, pull requests, reviews, and activity needed for project awareness. Do not continuously clone or index every repository.

The only GitHub write authorized during implementation is Codex creating/updating the dedicated private project repository under `moonishaider`. That authorization is not available to Hermes runtime.

