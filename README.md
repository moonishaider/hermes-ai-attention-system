# Hermes AI Attention & Intelligence System — Codex Handoff v2

**Prepared for:** Syed Moonis Haider  
**Reference date:** 1 August 2026  
**Purpose:** Let a fresh Codex session continue this project with the product context, architecture, risks, permissions, implementation plan, and user preferences already understood.

This package is the **authoritative design-and-implementation handoff**, not the finished application. Codex should verify time-sensitive technical details against current official sources and then build the system in substantial, tested milestones.

## Decisions in this revision

- **Codex builder:** GPT-5.6 Sol with **Medium** reasoning.
- **Codex permissions:** **Full Access** with `approval_policy = "never"`, at Syed's explicit request.
- **Hermes runtime models remain unchanged:** DeepSeek V4 Flash for routine work, DeepSeek V4 Pro for difficult reasoning after verification, GPT-5.6 Luna for vision, and rare GPT-5.6 Terra review—using direct API billing.
- **Two-prompt start:** Prompt 1 proves understanding and checks GitHub access without implementing; Prompt 2 starts the substantial build.
- **GitHub sources:** `moonishaider` for Syed's personal repositories and `inside-success` for company repositories.
- **Build repository:** a dedicated **private** repository under `moonishaider`, preferably `moonishaider/hermes-ai-attention-system`.
- **No company writes:** Codex and the initial Hermes runtime may read authorized `inside-success` repositories, but must not modify them.

## Full Access safety posture

Full Access removes Codex's normal filesystem and network containment. It is convenient, but it cannot be made as safe as a sandbox merely through prompting. This package therefore uses defence in depth:

- a dedicated project marker and path preflight;
- project-local Codex **PreToolUse hooks** that block common destructive, outside-project, browser/computer-control, and external-write calls;
- project-local command rules that forbid deletion, privilege escalation, disk operations, destructive Git commands, direct pushes, and direct repository creation;
- protected guarded scripts for creating and pushing only the approved private personal repository;
- Git baseline and milestone commits for rollback;
- synthetic/redacted development data;
- strict secret exclusions and no writes to `inside-success`;
- narrow product action policies distinct from Codex's build permissions.

These controls materially reduce accidental harm but do not eliminate the residual risk of Full Access. Use a current Mac backup and a new empty project folder.

## Exact startup sequence

1. Create a **new empty folder**. Do not use your home directory, Desktop, Documents, Downloads, an existing repository, or a folder containing valuable files.
2. Extract this package into that folder and open the extracted root in Codex.
3. Confirm the session shows:
   - **Model:** GPT-5.6 Sol
   - **Reasoning:** Medium
   - **Permissions:** Full Access / no routine approval prompts
4. Mark the project as **trusted** so its `.codex/` configuration, hooks, and rules load.
5. Open `/hooks` (or the equivalent hooks screen), review the project-local hook definitions, and trust them once. This is a one-time safety setup, not per-command approval.
6. The package includes `.codex/config.toml`. If the UI or a higher-precedence configuration overrides it, manually select Sol / Medium / Full Access before continuing.
7. Paste the complete contents of `CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md`. Codex must only read, run non-destructive checks, verify GitHub access, acknowledge understanding, and stop.
8. After reviewing that acknowledgement, paste `CODEX_PROMPT_02_IMPLEMENTATION.md` in the **same Codex session**.

## GitHub behavior

During Prompt 1, Codex may only perform credential-safe, read-only checks such as authentication status, authenticated identity, and repository visibility. It must not clone repositories, initialize Git, create a repository, push, open issues or pull requests, or modify either GitHub owner.

During Prompt 2, Codex should initialize this project, create a baseline commit, and then create or attach the dedicated private repository under `moonishaider`. Direct `git push` and direct `gh repo create` are intentionally blocked; Codex must use the guarded scripts under `scripts/`. The project must never be pushed to `inside-success` or any unrelated repository.

The finished Hermes assistant should connect to GitHub through the current official GitHub MCP/native route where practical. Start with two logical read-only connections—personal and company—with minimal tool exposure, immutable owner/repository/commit/path provenance, and negative tests proving that write/admin tools cannot execute.

## Package map

- `AGENTS.md` — permanent repository instructions automatically loaded by Codex.
- `CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md` — first prompt; no implementation or file/external writes.
- `CODEX_PROMPT_02_IMPLEMENTATION.md` — second prompt; substantial implementation.
- `FULL_CONTEXT_HANDOFF.md` — consolidated user context, decisions, concerns, and intent.
- `MANIFEST.md` — required reading checklist.
- `PACKAGE_VALIDATION_REPORT.md` — local structural and safety-control validation results and deferred live checks.
- `.codex/config.toml` — requested model/effort/permissions and safety-related shell settings.
- `.codex/hooks.json` and `.codex/hooks/` — deterministic pre-tool safety checks.
- `.codex/rules/safety.rules` — forbidden shell-command prefixes.
- `scripts/` — preflight, safety tests, GitHub verification, private-repository creation, and guarded push helpers.
- `config/github_scope.example.json` — source and destination policy example.
- `docs/` — complete product, architecture, integration, security, roadmap, and acceptance specifications.
- `templates/` — reusable specialist, connector, approval, milestone, security, and test templates.

## Definition of success

The first production-worthy release lets Syed use one Hermes-based assistant to understand what changed across authorized sources; resume work from Codex and GitHub; recover commitments and open loops; manage tasks; prepare for meetings; receive concise context-switch briefings; research purchases; use voice with a live text overlay; inspect the screen only on request; and preview/approve a correctly formatted Inside Success daily activity update—without unauthorized or harmful external actions.
