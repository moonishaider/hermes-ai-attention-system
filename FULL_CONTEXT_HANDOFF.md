# Full Context Handoff

## Why this document exists

Syed Moonis Haider has spent several messages exploring an advanced personal AI system. He wants a fresh Codex session to feel like a continuation of that planning, not a restart. This document captures the product intent, concerns, corrections, and tone behind the technical requirements.

## User intent

Syed is strongly pro-AI and works in an AI-heavy environment. He now has a limited budget and a temporary window of free time, so he wants to build something that creates durable value before he becomes busy again. He is not seeking a novelty “Jarvis” imitation. A Jarvis-like voice/personality is welcome, including occasional sarcasm, but the core product is an **AI attention and intelligence system**.

The assistant should know what is happening across the information Syed is entitled to access, help him remember what he might otherwise forget, reduce context-switching, recover unfinished work, maintain tasks, surface commitments and contradictions, prepare for meetings, research purchases, and eventually perform carefully approved actions.

The desired result is more advanced than a normal chatbot. It should have memory, evidence, tools, voice, screen context, specialist capabilities, and a path toward controlled action. The system must remain useful rather than becoming over-engineered infrastructure.

## Identity and work contexts

Syed’s contexts currently include:

- **Inside Success:** his company/job. Colleagues generally call him “Syed.” Zoom may transcribe this as “Sid.”
- **Mitchell:** a separate Upwork client. This is not Inside Success work.
- **Personal:** finances, taxes, shopping, side projects, personal email, planning, and other personal matters.
- **Other clients/projects:** future Upwork clients and projects are expected.
- **Mixed:** some ChatGPT/Codex work or a project may legitimately span contexts.
- **Unknown:** ambiguous information must be held for clarification rather than guessed into the wrong context.

He has two separate Slack workspaces: Inside Success and Mitchell. He may have separate work and personal email identities. He uses one ChatGPT account for several contexts, so context cannot be inferred solely from the ChatGPT account.

Chrome is currently organized as:

- a company Chrome profile for Inside Success;
- “Profile 1” for personal use, Upwork, Mitchell, and other client work.

Syed does not want a third browser profile created merely for Hermes. The system must explicitly choose and display the intended existing profile before any side-effecting browser action.

## User communication preferences

Syed dictates many messages, so spelling or transcription may be imperfect. Interpret intent rather than treating every phrase literally.

He prefers concise, relevant output and dislikes repetition or overwhelming lists. At the same time, he does not want important details omitted. The assistant should acknowledge quickly, show useful status while working, then provide a compact answer with source evidence.

Syed explicitly does not want an assistant that agrees with everything. He wants genuine pushback when his assumption is wrong, but not artificial disagreement. Technical claims should be re-verified because the field moves quickly.

## Selected foundation

Hermes Agent is the selected runtime/shell, subject to a current compatibility check. The architecture should not become irreversibly coupled to Hermes internals; adapters and domain logic should be modular enough to migrate if necessary.

The visible experience is:

- one master assistant;
- initially one Hermes profile;
- persistent specialist modules;
- temporary workers/reviewers only when isolation or parallel reasoning is useful;
- one task/memory/evidence experience.

Multiple profiles do not inherently multiply API cost, but the user prefers one initial profile because separate visible bots would add management and routing complexity.

## Specialists

“Tax researcher,” “meeting assistant,” “project planner,” “shopping researcher,” “financial adviser,” and “daily reporter” are examples, not the final list.

A specialist should persist as a package containing:

- role and boundaries;
- trusted domain instructions;
- tool allowlist;
- memory namespace;
- source requirements;
- templates;
- quality checks;
- test cases.

It is loaded only when needed, so it consumes no model tokens while idle. A difficult tax task might spawn an isolated analysis worker and a separate reviewer; a simple meeting summary may run in the main assistant with the meeting skill loaded.

Adding a specialist later must be easy. The system needs a registry, a template, and a generator/scaffolder rather than hand-wiring a new agent across the architecture.

## Information sources and desired awareness

High-priority sources include:

- Codex sessions/history/memories and repository activity;
- ChatGPT conversations that contain important context;
- two Slack workspaces;
- work and personal Gmail;
- Zoom meetings, recordings, and transcripts;
- Google Calendar;
- selected documents/files;
- current screen only after explicit activation;
- web research.

Codex history is especially important because much of Syed’s work happens there. It should be ingested incrementally and read-only, with source/session/repository/timestamp provenance.

For Zoom, Syed has developer-level access and wants useful context from department meetings even when he did not attend or was on holiday. The system should not assume “not personally attended” means irrelevant. It should preserve meeting ownership, attendees, source group, date, and transcript attribution. It should recognize “Syed” and possible “Sid” transcription variants.

## ChatGPT history reality

Syed does not need his entire multi-year ChatGPT history. A configurable backfill beginning around April or May 2026 is likely enough.

He rejected a browser extension as the main ongoing synchronization method because it feels unreliable. The implementation must be honest: there is no assumed official continuous API for a personal ChatGPT account’s complete history.

The supported plan is:

1. import one official ChatGPT account export;
2. filter by a configurable start date and optionally selected conversations;
3. automatically ingest Codex history from local official files;
4. provide a simple local “promote/send this ChatGPT context to Hermes” action through ChatGPT Work/desktop or a watched context inbox;
5. optionally provide an explicit “sync the currently open ChatGPT conversation” desktop automation adapter, clearly marked experimental and never used as hidden background scraping;
6. reconcile periodically with a new official export.

Raw conversation text is evidence, not durable truth. The system should promote only stable facts, decisions, commitments, and project state into trusted memory.

## Memory and evidence

Accuracy matters more than maximum speed, though both matter.

The system should distinguish:

1. **Identity/preferences:** concise style, sarcasm preference, naming, communication rules.
2. **Trusted memory:** stable facts, confirmed decisions, people, projects, and specialist conclusions.
3. **Operational state:** tasks, deadlines, commitments, blockers, unanswered questions, and next actions.
4. **Evidence:** source records from Slack, Gmail, Zoom, ChatGPT, Codex, documents, and web research.

Every meaningful answer should be able to show source, context, date, and whether it is confirmed, inferred, or uncertain. The model should not transform its own guess into memory.

Hermes’s built-in compact memory can retain critical preferences. Hermes Kanban or its current equivalent should hold tasks/open loops. A lightweight local evidence index may be required for Codex/ChatGPT history. Prefer embedded SQLite/FTS and native capabilities before adding a server, Postgres, or vector database. Add embeddings only after tests show a real retrieval gap.

## Context separation and flexibility

The assistant must be intelligent enough to understand overlap, but security and provenance cannot depend only on intelligence.

Each item receives:

- immutable source identity: account, workspace, channel, meeting, file, session;
- semantic context labels: zero or more contexts;
- confidence;
- classification reason/version;
- sensitivity and permitted uses.

Initial labels are `inside-success`, `mitchell`, `personal`, `mixed`, and `unknown`, but contexts are data, not hard-coded branches. A new client/project should be added through configuration.

The master assistant may search several contexts when Syed explicitly asks a cross-context question. It must not silently leak company/client information into an unrelated outgoing message.

## Safety posture

Syed is not mainly worried about model providers seeing data. His central concern is an AI taking an unauthorized, harmful, or malicious action.

External systems begin read-only. The assistant may write to its own local task board, memory, evidence index, drafts, reports, and audit logs.

Action authority should be introduced in stages:

1. observe;
2. propose;
3. shadow what it would do;
4. preview and approve one action;
5. allow a narrowly constrained reversible action;
6. expand only after measured reliability.

Personal workflows may be somewhat more flexible because only Syed is affected. Company and client workflows must be stricter because other stakeholders are involved.

Never allow unattended payments, purchases, tax filing/submission, credential or permission changes, destructive deletion, or broad external communication.

## Daily Inside Success activity report

At the end of a workday, the system should collect evidence of work Syed actually performed for Inside Success from Codex, company Slack, meetings, tasks, and project activity. It should produce the report in the company’s required format, show an exact preview, allow edits, and publish only after approval.

The eventual write capability must be a narrow action such as:

`publish_inside_success_daily_activity(approved_text)`

It must be locked to the configured Inside Success workspace and channel. The master model should not receive an unrestricted generic Slack send tool.

The exact format, channel, and timing will be configured later and learned from examples.

## Browser, computer, screen, and shopping

Syed wants more than read-only eventually.

Screen viewing:

- only after an explicit wake/manual command such as “look at my screen”;
- never continuous streaming;
- screen capture permission can be granted before Accessibility/computer-control permission.

Browser/computer:

- include the architecture from the start;
- start with research/navigation and proposal;
- use preview/approval for form filling, cart changes, calendar changes, messages, downloads, and other side effects;
- map Inside Success actions to the company Chrome profile and personal/Mitchell/Upwork actions to Profile 1;
- display the active profile, domain, account, action, and target before side effects;
- never use unrestricted/YOLO mode.

Shopping research should search sites such as Noon KSA or Amazon, compare exact products, seller reliability, availability, and total prices. It may prepare options or a cart, but checkout/payment remains manual.

## Voice and desktop UX

The assistant should feel responsive. It may take time for deep work, but it should acknowledge quickly and stream statuses such as “checking company Slack” or “searching Codex history.”

Prefer a small number of user-managed tools. Hermes Desktop should be the visible product. The initial voice stack should use Hermes-supported providers and be benchmarked; the working preference is fast cloud STT such as Groq Whisper and free Edge TTS, avoiding ElevenLabs unless a later quality test justifies it.

A floating always-on-top overlay should show:

- what the assistant heard;
- current activity/status;
- answer text while it is spoken;
- source/context indicator;
- approve, cancel, interrupt, mute, and dismiss controls.

Personality may be dry and sarcastic in normal conversation. Serious modes—tax, finance, security, professional outgoing content—must suppress sarcasm and prioritize precision.

## Hardware and hosting

Syed uses an 8 GB Apple Silicon MacBook. The system must not make it unusable, but quality should not be reduced merely to save a small amount of RAM.

The main models are API-hosted, so their weights do not occupy local RAM. Avoid local LLMs, permanent GPU inference, unnecessary Docker stacks, local Postgres, and local embedding models in the initial version. Local components should be lightweight: Hermes Desktop, small services/plugins, SQLite/FTS, wake-word logic, and the overlay.

Start on the Mac. A later inexpensive CPU VPS may run 24/7 ingestion, scheduled checks, or a gateway while the Mac sleeps. Voice, screen, and direct computer/browser control remain local. Do not rent a continuous GPU VPS; it would cost more than API use and would not host the selected large models effectively.

## Models and cost

Use direct API billing rather than Syed’s ChatGPT/Codex subscription because his Codex allowance is already scarce.

Approved baseline:

- DeepSeek V4 Flash: ordinary conversation, classification, extraction, routing, and routine tool use.
- DeepSeek V4 Pro: difficult reasoning and important analysis, once current availability/support is verified.
- GPT-5.6 Luna: screenshots and image understanding.
- GPT-5.6 Terra: rare independent review for high-stakes work.
- Do not use GPT-5.6 Sol for routine Hermes runtime. Codex itself is intentionally configured to use GPT-5.6 Sol at Medium effort for implementation.

There is market interest in Luna as a cheap general model. Build an evaluation harness using real representative tasks so routing can change based on measured quality, latency, and cost. Do not change the approved baseline merely because of hype.

Target operating cost is below $50/month. Syed could stretch to $100 only for a meaningful benefit. Add soft and hard cost alerts, per-provider usage accounting, request budgets, and a fail-safe that stops optional background processing before exceeding the cap.

## Important product features

Required or strongly desired:

- universal source-backed search;
- daily attention queue;
- context-switch handoff;
- tasks/to-do management;
- open-loop and commitment tracking;
- contradiction detection;
- meeting preparation and follow-up;
- project resumption after inactivity;
- uncertainty inbox;
- source citations and confidence;
- automation discovery;
- ROI/time-saved tracking;
- daily company activity report;
- web and shopping research;
- voice and overlay;
- explicit screen understanding;
- controlled browser/computer actions;
- flexible specialist modules.

## Build approach

Use this planning package and Codex as the builder. Hermes Desktop becomes the runtime product. Codex should implement in substantial milestones rather than asking for a prompt after every trivial file.

Codex will run with Full Access and no per-command approval prompts by Syed’s explicit choice. It should implement in substantial milestones, use verified official sources, and stop only for genuinely interactive credentials/OAuth/macOS permissions or unresolved product decisions.

Because Syed has seen reports of coding agents deleting files, the repository carries strict Full Access safeguards: isolated workspace, current backup, command-deny rules, no automated deletion, Git baseline and milestone checkpoints, secret protection, narrow outside-write logging, and strict GitHub destinations. Full Access still has residual risk, which must be acknowledged rather than hidden.

The architecture should be sufficiently complete now that adding later specialists, sources, or actions does not require a second high-level rebuild.


## Latest implementation decisions: Codex mode, two prompts, and GitHub

Syed wants the build performed with **GPT-5.6 Sol at Medium effort in Codex Full Access**, without approval prompts after every command. He understands the risk and prefers speed and autonomy, but expects all possible precautions so Codex does not harm unrelated files or repositories. This changes Codex’s build environment only; the Hermes runtime model router remains DeepSeek V4 Flash/Pro, GPT-5.6 Luna for vision, and rare Terra review through direct APIs.

The start uses two prompts. Prompt 1 must read all handoff files, verify understanding, inspect safety/Git state, check read access to GitHub owners `moonishaider` and `inside-success`, report issues, explicitly state readiness, and stop. Prompt 2 then performs the substantial implementation rather than asking for many baby-step prompts.

GitHub is now a first-class Hermes source:

- `moonishaider` is Syed’s personal GitHub owner/workspace.
- `inside-success` is the company GitHub owner/workspace used by his department.
- Codex should verify exact access and keep this project in a dedicated private repository under `moonishaider`.
- Codex and Hermes must not write to `inside-success` in this version.
- Hermes should use two separate read-only GitHub connections so it can understand repositories, code/docs, commits, issues, pull requests, reviews, and project activity while preserving owner/repository provenance.
- GitHub activity should improve project resumption, attention queues, context, and the daily Inside Success activity report.
- New GitHub owners, repositories, specialists, sources, and actions must be configurable rather than requiring a high-level rebuild.

After Codex completes, Syed expects a tested private repository and local setup plus precise manual steps for API keys, OAuth, macOS permissions, imports, calibration, and supervised activation.
