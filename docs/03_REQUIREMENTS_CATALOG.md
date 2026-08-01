# Requirements Catalog

Requirements use stable IDs so Codex can trace them to code, tests, and milestone status.

## Product and interaction

- **PRD-001:** One visible master assistant.
- **PRD-002:** Initially one Hermes profile.
- **PRD-003:** Advanced attention/intelligence product, not a basic chatbot.
- **PRD-004:** Fast acknowledgement and streamed progress/status.
- **PRD-005:** Concise default responses without omitting material information.
- **PRD-006:** Dry/sarcastic optional personality; serious domains suppress sarcasm.
- **PRD-007:** Floating overlay showing transcript, status, response, source/context, and approval controls.
- **PRD-008:** Voice wake/manual activation, interruption, and spoken streaming.
- **PRD-009:** Explicit on-demand screen capture; no continuous stream.
- **PRD-010:** Web and shopping research, including exact product/seller/price comparison.

## Context and provenance

- **CTX-001:** Immutable source/account/workspace/session provenance for every evidence item.
- **CTX-002:** Semantic labels initially include Inside Success, Mitchell, Personal, Mixed, and Unknown.
- **CTX-003:** Multiple labels and confidence scores are supported.
- **CTX-004:** Contexts are configuration/data and can be added without code changes.
- **CTX-005:** Cross-context queries are supported when authorized.
- **CTX-006:** Outgoing actions cannot silently combine unrelated contexts.
- **CTX-007:** Existing Chrome profiles are mapped to contexts; no third profile is required.
- **CTX-008:** Recognize Syed/Sid aliases in Zoom when context supports it.

## Sources and integrations

- **SRC-001:** Two Slack workspaces.
- **SRC-002:** Work and personal Gmail.
- **SRC-003:** Google Calendar.
- **SRC-004:** Zoom meetings, recordings, transcripts, and accessible department context.
- **SRC-005:** Codex history, sessions, memories, repository activity, and Git evidence.
- **SRC-006:** Historical ChatGPT export with configurable date filter.
- **SRC-007:** Ongoing explicit ChatGPT context relay.
- **SRC-008:** Selected documents/files.
- **SRC-009:** Current web research with source metadata.
- **SRC-010:** Use Hermes native/official MCP connectors first; custom adapter only when required.
- **SRC-011:** Incremental ingestion with checkpoints and no duplicate processing.
- **SRC-012:** Source access failures and stale data are surfaced, not hidden.

## Memory, evidence, and tasks

- **MEM-001:** Separate identity, trusted memory, operational state, and evidence.
- **MEM-002:** Raw source data is not automatically trusted memory.
- **MEM-003:** Memory writes begin with explicit proposal/approval.
- **MEM-004:** Important answers include source, date, context, confidence, and confirmed/inferred state.
- **MEM-005:** Durable tasks/to-do list.
- **MEM-006:** Open loops, commitments, deadlines, blockers, decisions, unanswered questions.
- **MEM-007:** Contradiction detection with linked evidence.
- **MEM-008:** Uncertainty inbox for ambiguous classification or extraction.
- **MEM-009:** Embedded/lightweight local state appropriate for 8 GB RAM.
- **MEM-010:** Retrieval quality is measured before adding vector infrastructure.
- **MEM-011:** Retention, deletion, redaction, and re-indexing controls exist.
- **MEM-012:** Audit history exists for memory/task changes.

## Specialists

- **SPC-001:** Specialists persist as modules, not permanent running processes.
- **SPC-002:** Each specialist has instructions, tool policy, memory scope, templates, and tests.
- **SPC-003:** Specialists are invoked on demand.
- **SPC-004:** Complex work may spawn isolated worker/reviewer agents.
- **SPC-005:** New specialist scaffolding is registry/template driven.
- **SPC-006:** Example modules do not limit future modules.
- **SPC-007:** High-stakes modules require current authoritative sources and independent review.
- **SPC-008:** Tax/finance calculations use deterministic code and remain user-submitted.

## Attention and productivity

- **ATT-001:** Daily attention queue ranked by urgency, impact, and need for Syed.
- **ATT-002:** Context-switch handoff.
- **ATT-003:** Meeting preparation and post-meeting decisions/actions.
- **ATT-004:** Project resumption after inactivity.
- **ATT-005:** Automation discovery from repeated workflows.
- **ATT-006:** ROI/time-saved tracking.
- **ATT-007:** End-of-day Inside Success activity report generated from evidence.
- **ATT-008:** Daily report follows configurable examples/format.
- **ATT-009:** Report is previewed and approved before publication.
- **ATT-010:** Report publisher is locked to one configured workspace/channel.

## Models, performance, and cost

- **MOD-001:** Direct API keys; no default use of ChatGPT/Codex subscription allowance.
- **MOD-002:** DeepSeek V4 Flash baseline for routine work.
- **MOD-003:** DeepSeek V4 Pro baseline for complex work after verification.
- **MOD-004:** GPT-5.6 Luna baseline for vision.
- **MOD-005:** GPT-5.6 Terra used only for rare high-stakes review.
- **MOD-006:** GPT-5.6 Sol is not used for routine Hermes runtime; Codex uses Sol/Medium only as the selected build model.
- **MOD-007:** Routing is configurable and benchmarked.
- **MOD-008:** Monthly soft alert and hard budget cap.
- **MOD-009:** Usage/cost attribution by feature, model, and context.
- **MOD-010:** Fast first acknowledgement and streaming.
- **MOD-011:** Accuracy, citation, and retrieval tests take priority over superficial latency.

## Actions and safety

- **ACT-001:** External integrations start read-only.
- **ACT-002:** Local memory/task/draft/audit writes are allowed.
- **ACT-003:** Every external action has risk class, target, exact preview, approval, and audit event.
- **ACT-004:** Personal and professional policies may differ.
- **ACT-005:** No unattended payment, purchase, tax/legal submission, credential/permission change, destructive deletion, or broad message sending.
- **ACT-006:** Browser profile/account/domain/target shown before side effects.
- **ACT-007:** Company daily report uses a narrow deterministic publisher.
- **ACT-008:** Community skill installation requires source review, pinning, and approval.
- **ACT-009:** No unrestricted/YOLO computer-use mode.
- **ACT-010:** Action shadow mode exists before execution is enabled.
- **ACT-011:** Idempotency and duplicate-send protection for external writes.
- **ACT-012:** Emergency disable/kill switch exists.

## Operations and implementation

- **OPS-001:** Start on local Mac; later optional CPU VPS for light always-on work.
- **OPS-002:** No permanent GPU VPS or local frontier LLM.
- **OPS-003:** Pin stable Hermes version and support rollback.
- **OPS-004:** Backups for state/config and tested restoration.
- **OPS-005:** Secrets kept outside Git.
- **OPS-006:** Current official documentation verified at implementation.
- **OPS-007:** Structured logs avoid leaking sensitive content.
- **OPS-008:** Health, connector freshness, cost, and queue status visible.
- **OPS-009:** Substantial milestones with acceptance gates.
- **OPS-010:** Codex uses the user-selected Full Access/no-approval mode while obeying the documented hard safety protocol, command-deny rules, Git rollback discipline, and repository boundaries.


## GitHub source and build repository

- **GIT-001:** Verify GitHub access to owners/accounts `moonishaider` and `inside-success`.
- **GIT-002:** Keep the project in a dedicated private repository under `moonishaider` when access permits.
- **GIT-003:** Never write implementation changes to `inside-success` or unrelated repositories.
- **GIT-004:** Hermes has two separately scoped read-only GitHub connections, one per owner/account.
- **GIT-005:** GitHub retrieval covers repositories, selected code/files, commits, issues, pull requests, reviews, and relevant checks/activity.
- **GIT-006:** GitHub evidence preserves owner, repository, visibility, branch, commit SHA, path, issue/PR identifier, actor, and timestamp.
- **GIT-007:** Runtime tests prove GitHub write/admin tools are absent or blocked.
- **GIT-008:** Relevant Inside Success GitHub activity can support attention queues, project resumption, and daily activity reporting.
- **GIT-009:** Future owners/repositories can be added through configuration rather than code changes.

## Codex handoff execution

- **CDX-001:** Prompt 1 reads and verifies the entire handoff, validates safety/GitHub access non-destructively, makes no file/system/external changes, acknowledges understanding, and stops before implementation.
- **CDX-002:** Prompt 2 performs substantial implementation rather than only producing another plan.
- **CDX-003:** Codex build configuration is GPT-5.6 Sol, Medium reasoning, Full Access, and no approval prompts.
- **CDX-004:** Full Access is constrained by deterministic PreToolUse/SubagentStart hooks, command-deny rules, no-deletion policy, external-write log, Git checkpoints, and secret protection.
- **CDX-005:** The only authorized GitHub write is the dedicated private project repository under `moonishaider`.
