# Repository Blueprint and Engineering Standards

This is a target organization, not a command to duplicate functionality that Hermes already provides. Codex should first map the current Hermes extension/plugin/skill layout and then preserve these boundaries in the most native form.

## Suggested logical layout

```text
/
  AGENTS.md
  README.md
  implementation/          # audits, risk register, milestone records
  config/                  # non-secret schemas and examples
  policies/                # context, tools, actions, budgets
  specialists/             # registry and persistent specialist packages
    _template/
    meeting/
    project-resumption/
    daily-report/
    research-shopping/
    tax-finance/
  src/ or plugins/
    context/                # provenance, labels, routing
    evidence/               # storage, FTS, citations, checkpoints
    history/                # Codex and ChatGPT bridge
    memory_tasks/           # promotion, tasks, contradictions
    attention/              # queue, handoff, ROI, automation discovery
    actions/                # proposals, policy, executor, kill switch
    ui_overlay/             # local status/transcript/approval surface
    integrations/           # adapters only when native tools need wrapping
      github/                # two read-only GitHub owner connections and provenance
    models/                 # routing, cost ledger, evaluation hooks
  tests/
    unit/
    contract/
    integration/
    security/
    evaluations/
    fixtures/synthetic/
  scripts/                  # safe project-local utilities
  migrations/
  docs/
  runtime-data/             # untracked; created at runtime
```

## Engineering standards

- Prefer the language and extension mechanism native to the verified Hermes version.
- Use typed schemas for evidence, context labels, actions, approvals, and specialist manifests.
- Validate all external/model-generated structured data at boundaries.
- Keep domain logic separate from provider-specific SDKs.
- Make source ingestion idempotent and restartable.
- Make external actions idempotent, preview-hashed, and auditable.
- Use dependency injection/interfaces where it improves tests and replaceability; avoid abstract layers with only one trivial implementation.
- Use structured errors and user-visible failure states.
- Use migrations for persistent state.
- Use synthetic fixtures by default.
- Keep secrets and real data outside Git.
- Pin dependencies and capture lockfiles.
- Prefer small reviewed dependencies over large frameworks for simple functions.
- Do not expose raw provider SDK clients or credentials to specialist prompts.

## Configuration

Configuration should distinguish:

- non-secret committed defaults;
- local user settings;
- secrets/credential references;
- generated runtime state;
- policies requiring explicit approval.

Provide schema validation and a configuration doctor that reports missing/invalid settings without printing secrets.

## Testing and quality

Minimum local commands should cover:

- format/lint;
- type checking where applicable;
- unit tests;
- contract tests;
- security tests;
- synthetic end-to-end scenario;
- requirement traceability check;
- secret scan;
- migration test.

Codex should put the exact verified commands in the root README after choosing the implementation stack.

## Documentation generated during implementation

- architecture decision records for consequential choices;
- connector scope inventory;
- specialist registry reference;
- data retention guide;
- action policy guide;
- local troubleshooting/doctor guide;
- backup/restore guide;
- current limitations.

## Commit strategy

- baseline handoff commit;
- one coherent commit or small series per milestone boundary;
- requirement IDs in commit descriptions;
- no real data or secrets;
- no “cleanup” commits that hide broad unrelated changes;
- preserve rollback points before migrations, Hermes updates, or permission changes.


## Build repository and documentation

Use a dedicated private repository under `moonishaider` when access permits. Keep implementation reports and architectural decisions versioned there, but exclude secrets, real source data, imported histories, credentials, runtime databases, and private diagnostic content. `inside-success` repositories are sources only and are never implementation remotes.

## Guarded Full Access build controls

Keep `.codex/config.toml`, project hooks, command rules, the project marker, and guarded scripts under version control and treat them as protected infrastructure. The PreToolUse hook blocks common destructive/path-escape/external-write operations before execution; command rules provide a second independent prefix-level control. Run `scripts/verify_safety_controls.sh` before implementation and after any Codex update.

Direct `git push` and direct `gh repo create` are blocked. The guarded scripts verify the project marker, approved owner/repository namespace, Git state, private visibility, diff validity, and obvious secret-bearing tracked paths. Do not weaken these controls merely because they inconvenience a task; choose a safer implementation path and document any genuinely required exception for Syed.
