# Browser, Computer Actions, and Approvals

## Position

Browser and computer capabilities belong in the initial architecture, but authority is enabled gradually. The goal is useful action without relying on model obedience alone.

## Action classes

### A0 — Read-only observation

Examples:

- web search;
- read Slack/email/calendar/Zoom;
- inspect explicit screenshot;
- inspect Codex history;
- navigate/read a public product page.

May run automatically within configured policy.

### A1 — Local reversible state

Examples:

- update Hermes task board;
- create a local draft;
- save a proposed memory;
- write an internal report;
- update local preferences.

Allowed with audit and undo/versioning.

### A2 — Reversible external proposal

Examples:

- create an email draft;
- prepare a calendar event;
- fill a form without submitting;
- add an item to a cart;
- download to an isolated project-controlled folder.

Requires preview; execution policy may become streamlined on the personal side after shadow testing.

### A3 — External communication or consequential reversible action

Examples:

- send the daily company report;
- send an email;
- post to Slack;
- create/update a calendar event;
- submit a non-financial form.

Requires exact target, full payload preview, explicit approval, expiry, and idempotency.

### A4 — Manual-only/prohibited for autonomous execution

- payment/purchase/checkout;
- tax/legal filing submission;
- credential/permission changes;
- permanent deletion;
- broad or mass communication;
- installing unreviewed skills/software;
- destructive computer/file operations.

The assistant may guide or prepare, but Syed executes the final action.

## Existing Chrome profiles

Do not create a third profile.

Policy mapping:

- company profile -> Inside Success;
- Profile 1 -> personal, Mitchell, Upwork, other clients;
- mixed/unknown -> no side effect.

Before a side effect, the overlay must show:

- profile name;
- detected account;
- website/domain;
- action;
- exact target;
- submitted text/data;
- risk class.

## Browser implementation preference

Prefer deterministic APIs/MCP for Slack, email, calendar, and other structured actions. Use browser automation for websites without a suitable API and for personal research.

Never use unrestricted Hermes computer-use/YOLO mode. Connect to an existing browser only after a manual setup and test with synthetic/non-sensitive pages.

## Approval object

Required fields:

- proposal ID;
- action type;
- context;
- risk class;
- target and destination;
- exact payload;
- browser profile/account;
- originating user request;
- evidence/source references;
- generated timestamp;
- expiry;
- idempotency key;
- policy checks;
- preview hash;
- approval identity/time;
- execution result.

Any payload change after approval invalidates the approval.

## Daily report publisher

Expose a narrow executor method, not generic Slack writing.

Inputs:

- approved report text;
- report date;
- preview hash;
- approval token.

Destination is server/config locked. Reject arbitrary workspace/channel parameters.

## Personal flexibility

After a successful shadow period, personal A2 actions may allow “approve similar actions for this session” with a visible scope and revocation. A3 and A4 remain explicit.

## Skill/software installation

- discovery/listing allowed;
- source download only after approval;
- source review and dependency scan;
- pinned version/hash;
- no lifecycle/post-install scripts without review;
- install into isolated project environment;
- test with tools disabled;
- separate permission approval before activation.

## Kill switch

Provide:

- stop current action;
- disable all external write tools;
- revoke/disable executor;
- disconnect browser control;
- revoke tokens/manual instructions;
- safe-mode startup.
