# Prompt 2 — Build the System

Proceed with the substantial implementation of the **Hermes AI Attention & Intelligence System** using the entire repository handoff and everything established in Prompt 1.

Use the selected **GPT-5.6 Sol / Medium / Full Access** Codex session. Work autonomously in large, coherent milestones rather than asking for routine approvals. Full Access does not override `AGENTS.md`, the project-local hooks and rules, the marked project boundary, GitHub destination restrictions, or the finished product’s separate approval policies.

Start by running the safety preflight, confirming the real root, initializing Git only there if required, creating a baseline rollback commit, and creating all implementation records required by `AGENTS.md`. Preserve files through Git or project-local quarantine; never use broad deletion, destructive cleanup, privilege escalation, history rewrites, or unrelated system changes.

Then implement the largest safe, working portion possible:

1. Verify current official Hermes, Codex/OpenAI, model-provider, GitHub MCP, Google, Slack, and Zoom capabilities. Record checked dates, versions, limitations, and fallbacks instead of assuming the handoff is still exact.
2. Build one visible Hermes-based assistant with immutable source provenance, flexible context classification, source-backed retrieval, efficient memory/tasks/open loops, attention and context-switch features, audit/cost controls, voice with a live text/status overlay, explicit screen viewing, and staged preview/approval actions.
3. Implement first-class Codex-session/history ingestion and the supported ChatGPT historical backfill plus practical ongoing context-relay workflow. Do not invent an unsupported continuous ChatGPT-history API or silently scrape the account.
4. Implement registry/template-driven persistent specialist modules and integration adapters so future specialists, clients, workspaces, tools, and sources can be added without creating another assistant or rewriting the architecture. Current named specialists are examples, not a fixed list.
5. Add GitHub as a first-class Hermes evidence source using the current official supported route where practical. Configure separate logical **read-only** connections for `moonishaider` and `inside-success`, preserve owner/repository/ref/SHA/path/issue/PR provenance, expose no runtime write/admin tools, and test attempted writes negatively. Never modify `inside-success`.
6. Preserve the approved Hermes runtime router: **DeepSeek V4 Flash** for routine work, **DeepSeek V4 Pro** for difficult reasoning after verification, **GPT-5.6 Luna** for vision, and rare **GPT-5.6 Terra** review through direct APIs. Codex using Sol does not make Sol a routine Hermes dependency.
7. Implement synthetic fixtures, unit/contract/integration/security/evaluation tests, requirement traceability, configuration diagnostics, secret scanning, backup/restore guidance, and honest limitations. Install only reviewed, pinned, project-local dependencies from official sources.
8. When GitHub access permits, create or attach the dedicated **private** repository under `moonishaider`, preferably `hermes-ai-attention-system`, using only `scripts/safe_create_private_repo.sh` and `scripts/safe_git_push.sh`. Version the code, architecture, implementation reports, tests, and runbooks there; never commit credentials, real source data, imported histories, runtime databases, or private diagnostic content.
9. Produce exact step-by-step manual runbooks for API keys, OAuth/account selection, GitHub/Slack/Google/Zoom authorization, macOS permissions, ChatGPT backfill, calibration, and supervised action testing. Continue every unblocked task; stop only where Syed must interact with an account, permission dialog, credential, or genuinely unresolved decision.

During the build, do not send real Slack/email messages, change real calendars, purchase, submit forms, operate company/client accounts, or use broad live browser/computer control. The sole authorized external write is the dedicated private project repository under `moonishaider` through the guarded scripts.

Do not stop after another high-level plan. Deliver working code, configuration, tests, documentation, rollback points, and the largest coherent safe implementation possible. Finish with a concise report of completed requirements, architecture, test/security results, GitHub status, exact manual next steps, and honest blockers or deferred items.
