# Integration Adapter Specification

## Provider/source

- Adapter ID:
- Provider:
- Version:
- Connection identity:
- Default context:
- Native Hermes / official MCP / custom fallback:

## Required capabilities

- Read tools:
- Write tools:
- Search/list/get semantics:
- Incremental sync/checkpoint:
- Attachments/resources:
- Rate limits:

## Permissions

- OAuth/API scopes:
- Why each scope is required:
- Scopes explicitly rejected:
- Tool allowlist:
- Credential storage:
- Revoke/disconnect steps:

## Provenance mapping

- Native item ID:
- Account/workspace:
- Channel/mailbox/meeting/repository:
- Timestamp/revision:
- Author/participants:
- URL/path/reference:
- Integrity/deduplication:

## Context policy

- Deterministic rules:
- AI classification:
- Mixed/unknown behavior:
- Outgoing-action constraints:

## Security

- Prompt-injection surface:
- Secret redaction:
- Content retention:
- External write class:
- Destination lock:
- Idempotency:

## Health and operations

- Freshness signal:
- Authentication status:
- Retry/backoff:
- Failure visibility:
- Logs/metrics:
- Re-index/recovery:

## Tests

- Mock fixtures:
- Contract tests:
- Permission tests:
- Duplication tests:
- Context leakage tests:
- Revocation test:
