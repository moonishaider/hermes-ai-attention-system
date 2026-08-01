# Two-Prompt Codex Execution Flow

## Why two prompts

Syed wants Codex to prove that it has absorbed the complete handoff and can see the required GitHub environments before it begins changing anything. The second prompt then authorizes a substantial autonomous implementation rather than dozens of baby-step prompts.

## Prompt 1 — understanding and access verification

`CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md` instructs Codex to:

- read the complete handoff and safety setup;
- run non-destructive preflight and safety-control tests;
- report Sol/Medium/Full Access when observable;
- verify credential-safe read visibility for `moonishaider` and `inside-success`;
- distinguish public access from authorized private access and report SSO/scope gaps;
- acknowledge its understanding and readiness.

Prompt 1 must make **no file, Git, system, browser, account, repository, or other external changes**. It must not create a verification report; its acknowledgement remains in the same Codex conversation and Prompt 2 creates the durable implementation records.

## Prompt 2 — substantial implementation

`CODEX_PROMPT_02_IMPLEMENTATION.md` authorizes Codex to:

- create the Git baseline, audits, plans, risk register, traceability, and rollback records;
- verify current official capabilities;
- implement and test the system in substantial coherent milestones;
- install reviewed project-local dependencies;
- create or attach the dedicated private personal GitHub repository through guarded scripts;
- continue every unblocked task until a genuinely interactive credential, OAuth, macOS permission, account selection, or unresolved decision requires Syed.

It does not authorize writes to `inside-success`, real business-account actions, destructive file operations, secret exposure, or unrestricted live browser/computer use during development.

## Session continuity

Use both prompts in the same Codex session so Prompt 2 retains Prompt 1’s verified understanding. The repository then becomes the durable source of truth: later sessions resume through `AGENTS.md`, the handoff, implementation records, Git history, and the latest milestone report.

## Expected Prompt 1 response

Only these headings should appear:

- **Understood**
- **Environment and safety**
- **GitHub access**
- **Issues**
- **Ready**

A response that starts coding, creates files, changes Git, or gives only a superficial summary fails the gate.

## Expected Prompt 2 behavior

Prompt 2 must not stop after producing another plan. It should implement, test, document, commit, and push the largest coherent safe portion possible, with exact manual runbooks for the few steps Syed must perform personally.
