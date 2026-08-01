# Manual Setup Runbook

Codex should update exact commands after verifying current official documentation. Syed performs credential and permission steps.

## Stage 1 — Safe project and two-prompt start

1. Create a current Mac backup, then extract the package into a new empty folder containing no valuable existing work.
2. Open the extracted root as a trusted Codex project using GPT-5.6 Sol, Medium reasoning, and Full Access as explicitly selected by Syed.
3. Review root `AGENTS.md`, the included `.codex/config.toml`, hooks, and rules. If higher-precedence settings override the project configuration, select Sol / Medium / Full Access manually.
4. Trust the project-local hooks once and run `scripts/verify_safety_controls.sh`.
5. Paste `CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md`. It must acknowledge understanding and GitHub access without changing anything.
6. In the same session, paste `CODEX_PROMPT_02_IMPLEMENTATION.md`. Prompt 2—not Prompt 1—initializes Git, creates the baseline commit, creates implementation records, and starts the build.

## Stage 2 — Provider accounts

Syed creates or selects direct API credentials for:

- DeepSeek;
- OpenAI API;
- STT provider if required;
- web search backend if required.

Store secrets through Hermes-supported credential storage, Keychain, or untracked environment files. Never paste them into documentation or commit them.

Set monthly provider budgets/alerts.

## Stage 3 — Hermes installation

After Codex verifies the current stable tagged release and installer:

1. review installer source/domain;
2. install Hermes Desktop/runtime;
3. choose blank-slate/minimal setup;
4. verify a normal text chat;
5. verify direct API routing;
6. keep tools disabled except the minimal tested set;
7. record installed version and rollback method.

Do not use a convenience setup that silently enables broad terminal/browser/computer tools.

## Stage 4 — Local runtime permissions

Grant one at a time only when the matching feature is ready:

- microphone;
- notifications;
- screen recording for explicit screenshots;
- Accessibility/computer control only in the controlled-action milestone.

Test and document revocation after each grant.

## Stage 5 — History

### Codex

Syed confirms the local Codex home/path if autodiscovery needs help. No credentials needed.

### ChatGPT

1. request official data export;
2. place ZIP in a dedicated import folder outside Git;
3. configure backfill start date (suggested 1 April 2026);
4. run preview showing conversations/date/size;
5. approve import;
6. delete or securely retain raw export according to preference.

Configure the local context relay for important future ChatGPT conversations.

## Stage 6 — Source OAuth

Connect one account at a time.

For each:

1. Codex/Hermes displays requested scopes and tools;
2. compare with official least-privilege documentation;
3. Syed performs OAuth;
4. verify only intended account/workspace;
5. run read-only test;
6. review tool inventory;
7. record revoke path.

Suggested order:

1. one Slack read-only connection;
2. one Gmail read-only connection;
3. second Slack;
4. second Gmail;
5. Calendar;
6. Zoom.

Do not approve write scopes until the controlled-action milestone.

## Stage 7 — Voice and overlay

1. choose wake phrase;
2. configure STT/TTS;
3. test names/accents;
4. configure overlay shortcut/position;
5. test interruption and cancel;
6. confirm no audio streams before activation.

## Stage 8 — Browser/screen

1. configure context-to-profile names;
2. connect in read-only/research mode;
3. test public/non-sensitive page;
4. verify profile/account indicator;
5. test explicit screenshot;
6. keep side effects disabled.

## Stage 9 — Daily report write

1. confirm exact Inside Success workspace/channel;
2. provide several approved format examples;
3. create narrow write credential/wrapper;
4. shadow-generate reports without sending;
5. test exact preview and edit;
6. send a supervised test;
7. verify idempotency and audit;
8. keep generic Slack send unavailable.

## Emergency steps

- activate safe mode;
- disable executor;
- revoke OAuth tokens;
- disconnect browser;
- quit Hermes;
- restore state backup;
- review audit log before re-enabling.


## Full Access start checks

Before Prompt 1, confirm a current backup, use a new dedicated folder, trust the project and its hooks so `.codex/config.toml`, `.codex/hooks.json`, and `.codex/rules/` load, and avoid exposing writable external drives. Prompt 1 must not implement or write to GitHub.

## GitHub activation

Codex first verifies access to `moonishaider` and `inside-success`. Prompt 2 may create/use the dedicated private personal project repository. Later, Syed completes two separate read-only Hermes GitHub authorizations and any required company SSO approval. Verify the exposed tool inventories before real use.

## After Codex finishes

1. Review the final implementation/security reports and private GitHub repository.
2. Enter API keys through the documented secret mechanism.
3. Complete Slack, Google, Zoom, and GitHub OAuth/account selection.
4. Grant only the required macOS permissions.
5. Import the chosen ChatGPT export and allow Codex-history ingestion.
6. Run synthetic tests, then supervised real-data read-only tests.
7. Calibrate contexts, aliases, report format, specialist behavior, voice, and retrieval.
8. Enable schedules and narrow approved actions only after the acceptance gates pass.
