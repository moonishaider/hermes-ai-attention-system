# Context, Provenance, and Routing

## Why both intelligence and hard boundaries are needed

Syed wants the assistant to understand overlap on its own. That is valid. However, a model’s semantic judgment cannot replace the factual identity of the source or the permission boundary of an account.

Every evidence item must retain two independent layers.

## Immutable provenance

Required fields include:

- source system;
- source connection/account ID;
- workspace/tenant;
- channel/mailbox/calendar/meeting/repository;
- source item ID;
- source timestamp and ingestion timestamp;
- author/participants;
- original URL/path/session reference where safe;
- connector/tool version;
- integrity hash or revision token where available;
- read permission/credential used;
- raw-content retention status.

Provenance is never overwritten by semantic classification.

## Semantic context

An item can have one or more labels:

- `inside-success`
- `mitchell`
- `personal`
- `mixed`
- `unknown`
- future configurable contexts

Each label contains:

- confidence;
- reason/evidence;
- classifier/model/rule version;
- user correction state;
- expiry/review date where appropriate.

## Classification order

1. deterministic source/account rules;
2. deterministic repository/channel/calendar/project mappings;
3. entities and explicit project/client names;
4. model classification;
5. user corrections;
6. unresolved ambiguity to `unknown` or `mixed`.

The model should not override a hard exclusion or destination policy.

## Cross-context retrieval

Allowed when:

- the user explicitly asks a cross-context question;
- the task requires it and the output remains private to Syed;
- policy permits each source;
- the response labels each source/context.

Before an outgoing professional action, the system must create a context-minimized draft that excludes unrelated evidence.

## Browser profile routing

Configured mapping:

- Inside Success -> company Chrome profile
- Mitchell/Personal/other Upwork -> Profile 1
- Mixed/Unknown -> no side-effect action until resolved

Read-only browsing/search may run automatically within the correct profile after the user has configured the connection. Any side effect shows:

- profile;
- signed-in account if detectable;
- domain;
- target;
- action;
- data to be submitted.

## User correction loop

Corrections should create durable routing rules only when they are generalizable. A one-off correction remains attached to the item.

Examples:

- “This ChatGPT conversation is both Mitchell and personal research” -> item labels.
- “All messages in #daily-activity belong to Inside Success” -> source rule.
- “The word Mitchell does not always mean the client” -> do not create an unsafe global keyword rule.

## Aliases

Initial person alias:

- `Syed Moonis Haider`
- `Syed`
- possible Zoom transcription `Sid`

Alias matching must use context and speaker metadata to avoid treating every “Sid” as Syed.

## Required tests

- correct routing for known source accounts;
- mixed-context ChatGPT/Codex items;
- unknown context quarantine;
- no Inside Success evidence in a Mitchell outgoing draft;
- no Mitchell evidence in a company daily report unless explicitly included and approved;
- browser profile selection;
- user correction persistence;
- source provenance survives reclassification.

## GitHub provenance

GitHub evidence must additionally retain connection identity, owner, repository, visibility, branch, commit SHA/object ID, path/line range, issue/PR/discussion identifier, actor, and timestamps. Content from `inside-success` normally receives the Inside Success semantic label, while content under `moonishaider` is classified by repository configuration and evidence rather than automatically assumed personal.

