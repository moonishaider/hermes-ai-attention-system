# Decision Log and Open Items

## Confirmed decisions

### Product

- Build an AI attention and intelligence system, not a basic chatbot.
- Use Hermes Agent as the initial runtime/shell, subject to current verification.
- One visible assistant and initially one Hermes profile.
- Persistent on-demand specialists; no permanently running “AI employee” processes.
- Seed specialists are examples, not the final module list.
- Build an extensible specialist registry/template.

### Context

- Inside Success and Mitchell are separate.
- Personal and future client contexts are required.
- Mixed and Unknown are first-class.
- Immutable provenance plus flexible AI labels.
- Existing Chrome profiles are used; no third Hermes browser profile.

### Sources/history

- Codex history is a first-class/high-priority integration.
- Recent ChatGPT context matters; entire multi-year history does not.
- Historical ChatGPT backfill can use one export filtered around April/May 2026.
- Browser extension is not the preferred ongoing ChatGPT method.
- No false claim of a perfect continuous ChatGPT-history API.
- Zoom may include accessible meetings Syed did not attend.
- Recognize Syed/Sid alias.

### Models/cost

- Direct API billing, not ChatGPT/Codex subscription allowance.
- Preserve DeepSeek Flash/Pro, Luna vision, Terra review baseline.
- Do not use GPT-5.6 Sol as the routine Hermes runtime model; Sol/Medium is intentionally used by Codex for this build.
- Target under $50/month; $100 only if justified.
- Start local; no GPU VPS/local frontier model.

### Safety/actions

- External read-only first, local writes allowed.
- Architecture includes controlled browser/computer actions.
- Personal side can be somewhat more flexible.
- Company/client actions use stricter approvals.
- Daily Inside Success report is previewed and sent only through a fixed-channel wrapper.
- No unattended high-impact actions.
- No unrestricted/YOLO mode.
- Codex itself must be workspace-isolated and non-destructive.

### UX

- Voice, wake/manual activation, fast acknowledgement, streaming status.
- Floating text/status/approval overlay.
- Explicit screen capture only.
- Sarcastic personality permitted outside serious contexts.

## Configurable/deferred items, not blockers

- Exact ChatGPT backfill start date: suggested `2026-04-01`; Syed may prefer May.
- Exact Inside Success daily report format, channel, and schedule.
- Which Slack/Gmail account is connected first.
- Final wake phrase/voice.
- Exact STT provider after benchmark.
- Exact Hermes memory provider/current feature choice after verification.
- Whether a light VPS is valuable after local trial.
- Which additional specialist modules are added first.
- Retention period for raw imported evidence.
- Whether optional explicit ChatGPT desktop capture is worth maintaining.

## Technical unknowns Codex must verify

- current stable Hermes version and compatibility;
- exact Hermes Desktop/plugin/overlay extension surface;
- current toolset/disabled-tool policy syntax;
- current provider routing and model support;
- current official Google Workspace MCP availability/scopes;
- current Slack MCP tools/scopes;
- current Zoom MCP tools/scopes;
- current Codex local history/memory formats;
- current ChatGPT desktop/export capabilities;
- current OpenAI/DeepSeek model names, endpoints, pricing, and tool/vision support;
- current Codex `.codex/config.toml` syntax.

## Pushback already accepted

- Trusting an agent because it has behaved well is not a security boundary.
- A cheap VPS is not an economical host for the selected large models.
- Context separation should not rely solely on model judgment.
- Full automatic ChatGPT-history synchronization cannot be promised without a supported interface.
- More permanently running agents do not inherently make the system more advanced.


## Decisions added 1 August 2026 — Full Access and GitHub

- Codex implementation uses GPT-5.6 Sol at Medium reasoning.
- Codex runs in Full Access with no per-command approval prompts by explicit user choice.
- Safety is handled through isolated workspace, backup, command-deny rules, no-deletion policy, Git checkpoints, external-write logging, and strict destination boundaries; residual risk is acknowledged.
- The handoff uses two prompts: acknowledgement/verification first, substantial implementation second.
- Codex must verify GitHub owners/accounts `moonishaider` and `inside-success`.
- The project is documented and pushed to a dedicated private repository under `moonishaider` when possible.
- Hermes receives separate read-only GitHub connections for both owners; `inside-success` writes remain disabled.
- The existing Hermes runtime model baseline is unchanged; Codex’s use of Sol is build-time only.
