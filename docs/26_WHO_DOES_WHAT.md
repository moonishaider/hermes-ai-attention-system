# Who Does What During the Build

## This ChatGPT planning conversation / handoff package

Role: **architect and product context**.

It provides:

- what Syed wants;
- why decisions were made;
- safety rules;
- architecture and requirements;
- implementation milestones;
- acceptance tests;
- current-source references.

After this package is placed in the repository, Codex should not need Syed to retell the conversation.

## Codex

Role: **builder, verifier, and implementation operator inside the isolated repository**.

Codex should:

- read the handoff;
- re-verify time-sensitive facts;
- map requirements to the current Hermes extension surfaces;
- scaffold and write code/config/tests;
- create synthetic fixtures;
- run tests and security checks;
- document exact manual steps;
- maintain requirement/risk/milestone records;
- autonomously perform project implementation, verified installs, tests, and the dedicated personal project-repository write; stop only for interactive credentials/OAuth/macOS permissions, real-account selections, or a genuinely unresolved product decision.

Codex is not the finished assistant and should not consume its own subscription allowance as the Hermes runtime.

## Syed

Role: **owner, approver, and holder of real credentials/accounts**.

Syed performs:

- selection of GPT-5.6 Sol / Medium / Full Access;
- confirmation of backup and isolated project folder;
- API key creation and secure entry;
- OAuth/login flows;
- selection of accounts/workspaces/channels;
- macOS permission grants;
- ChatGPT export request and secure import;
- examples of the daily report format;
- supervised external-action tests;
- product decisions that cannot safely be made configurable.

Syed should never paste credentials into prompts or commit them.

## Hermes Desktop/runtime

Role: **the daily product**.

Hermes provides the conversational runtime, tools/skills/integrations, sessions, voice, and Desktop experience. The custom project adds or configures the context, history, specialist, evidence, policy, attention, action, overlay, and evaluation behavior described in this handoff.

## Model APIs

Role: **reasoning and perception services**.

- DeepSeek V4 Flash: routine work.
- DeepSeek V4 Pro: complex reasoning after verification.
- GPT-5.6 Luna: screen/image understanding.
- GPT-5.6 Terra: rare independent review.

They are accessed through direct API billing and governed by the project router/budget.

## MCP/native integrations

Role: **controlled source and action adapters**.

They provide structured access to Slack, Google Workspace, Zoom, and other systems. They do not decide context or safety policy. Their exposed tools and OAuth scopes must be restricted by the project.

## Local project components

Role: **durable intelligence and control**.

- context/provenance router;
- Codex/ChatGPT history bridge;
- evidence index;
- tasks/open loops/memory promotion;
- specialist registry;
- attention engine;
- action proposal/executor;
- overlay;
- audit, cost, tests, and backups.

## Optional later VPS

Role: **light always-on support only**.

Possible: scheduled read-only collection, gateway, queues, health checks, encrypted backup.

Not initially: model hosting, voice, screen, signed-in browser control, or broad external action authority.


## GitHub roles

- Codex verifies both owners and writes only to the dedicated private project repository under `moonishaider`.
- Hermes reads both owners through separate read-only connections.
- `inside-success` is never a build destination and has no runtime write authority in this version.
