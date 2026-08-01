# Specialists and Extensibility

## Correct mental model

A specialist is **persistent configuration and knowledge, not a permanently running model process**.

It persists:

- identity/role;
- activation rules;
- domain policy;
- allowed tools;
- memory namespace;
- authoritative-source rules;
- model route;
- templates/schema;
- evaluation cases;
- version history.

It runs only when invoked.

## Invocation modes

### Inline skill

The main assistant loads the specialist skill and completes a contained task. Best for low-complexity work such as standard meeting summarization.

### Isolated worker

A temporary subagent receives the specialist package and a limited evidence set. Best for long, complex, or contamination-sensitive work.

### Worker plus reviewer

A specialist worker produces an answer; an independent reviewer checks evidence, calculations, policy, and uncertainty. Best for tax, finance, security, or important professional decisions.

Temporary workers do not lose the specialist’s durable memory; relevant memory is retrieved into the worker’s context.

## Registry design

Each module has a registry entry:

- stable ID;
- display name;
- version;
- owner;
- contexts;
- activation examples;
- tool allowlist;
- prohibited tools/actions;
- memory namespace;
- source policy;
- default/reviewer model class;
- seriousness/personality mode;
- output schema;
- test suite;
- status: draft/active/disabled/deprecated.

## Seed modules

The first implementation may include:

- meeting intelligence;
- project planning/resumption;
- daily Inside Success reporting;
- research/shopping;
- tax/financial research.

These are examples and validation cases, not a fixed product boundary.

## Easy module creation

Provide a command or generator equivalent to:

```text
create-specialist <id>
```

It should copy `templates/SPECIALIST_MODULE_TEMPLATE.md` and create the module skeleton, registry entry, test fixture, memory namespace, and disabled-by-default policy.

Adding a module must not require changes to the master prompt, router code, storage schema, or overlay.

## High-stakes rules

Tax/financial/legal/security modules must:

- retrieve current official sources;
- state jurisdiction and date;
- calculate with deterministic code;
- separate facts, assumptions, and advice;
- run a reviewer pass;
- show uncertainty;
- prohibit autonomous submission or payment;
- preserve evidence and calculation inputs.

## Module memory

A specialist may read:

- globally approved identity/preferences;
- its own memory namespace;
- explicitly relevant project/context memory;
- source evidence selected by policy.

It must not receive all unrelated memory by default.

## Quality and lifecycle

- version modules;
- retain evaluation sets;
- compare regressions before activation;
- require human approval for changed tool permissions;
- permit disabling a module without breaking the assistant;
- record which module/version produced a conclusion.
